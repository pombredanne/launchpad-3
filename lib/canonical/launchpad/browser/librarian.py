# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Browser file for LibraryFileAlias."""

__metaclass__ = type

__all__ = [
    'DeletedProxiedLibraryFileAlias',
    'FileNavigationMixin',
    'LibraryFileAliasMD5View',
    'LibraryFileAliasView',
    'ProxiedLibraryFileAlias',
    ]

from lazr.delegates import delegates
from zope.publisher.interfaces import NotFound
from zope.security.interfaces import Unauthorized

from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.launchpad.layers import WebServiceLayer
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.publisher import (
    canonical_url,
    LaunchpadView,
    RedirectionView,
    stepthrough,
    )
from canonical.launchpad.webapp.url import urlappend
from canonical.lazr.utils import get_current_browser_request
from canonical.librarian.client import url_path_quote
from lazr.restful.interfaces import IWebBrowserOriginatingRequest


class LibraryFileAliasView(LaunchpadView):
    """View to handle redirection for downloading files by URL.

    Rather than reference downloadable files via the obscure Librarian
    URL, downloadable files can be referenced via the Product Release URL,
    e.g. http://launchpad.net/firefox/1.0./1.0.0/+download/firefox-1.0.0.tgz.
    """

    def initialize(self):
        """Redirect the request to the URL of the file in the Librarian."""
        # Refuse to serve restricted files. We're not sure that no
        # restricted files are being leaked in the traversal hierarchy.
        assert not self.context.restricted
        # Perhaps we should give a 404 at this point rather than asserting?
        # If someone has a page open with an attachment link, then someone
        # else deletes the attachment, this is a normal situation, not an
        # error. -- RBC 20100726.
        assert not self.context.deleted, (
            "LibraryFileAliasView can not operate on deleted librarian files,"
            " since their URL is undefined.")
        # Redirect based on the scheme of the request, as set by
        # Apache in the 'X-SCHEME' environment variable, which is
        # mapped to 'HTTP_X_SCHEME.  Note that only some requests
        # for librarian files are allowed to come in via http as
        # most are forced to https via Apache redirection.
        self.request.response.redirect(
            self.context.getURL(
                secure=self.request.get('HTTP_X_SCHEME') != 'http'))


class LibraryFileAliasMD5View(LaunchpadView):
    """View to show the MD5 digest for a librarian file."""

    def render(self):
        """Return the plain text MD5 signature"""
        self.request.response.setHeader('Content-type', 'text/plain')
        return '%s %s' % (self.context.content.md5, self.context.filename)


class DeletedProxiedLibraryFileAlias(NotFound):
    """Raised when a deleted `ProxiedLibraryFileAlias` is accessed."""


class FileNavigationMixin:
    """Navigate to `LibraryFileAlias` hosted in a context.

    The navigation goes through +files/<filename> where file reference is
    provided by context `getFileByName(filename)`.

    The requested file is proxied via `LibraryFileAliasView`,
    making it possible to serve both public and restricted files.

    This navigation approach only supports domains with unique filenames,
    which is the case of IArchive and IBuild. It will probably have to be
    extended in order to allow traversing to multiple files potentially
    with the same filename (product files or bug attachments).
    """

    @stepthrough('+files')
    def traverse_files(self, filename):
        """Traverse on filename in the archive domain."""
        if not check_permission('launchpad.View', self.context):
            raise Unauthorized()
        library_file = self.context.getFileByName(filename)

        # Deleted library files result in NotFound-like error.
        if library_file.deleted:
            raise DeletedProxiedLibraryFileAlias(filename, self.context)

        # There can be no further path segments.
        if len(self.request.stepstogo) > 0:
            return None

        return RedirectionView(
            library_file.getURL(include_token=True),
            self.request)


class ProxiedLibraryFileAlias:
    """A `LibraryFileAlias` decorator for use in URL generation.

    The URL's output by this decorator will always point at the webapp. This
    is useful when:
     - the webapp has to be contacted to get access to a file (required for
       restricted files).
     - files might change from public to private and thus not work even if the
       user has access to the once its private, unless they go via the webapp.

    This should be used anywhere we are outputting URL's to LibraryFileAliases
    other than directly in rendered pages. For rendered pages, using a
    LibraryFileAlias directly is OK as at that point the status of the file
    is known.

    Overrides `ILibraryFileAlias.http_url` to always point to the webapp URL,
    even when called from the webservice domain.
    """
    delegates(ILibraryFileAlias)

    def __init__(self, context, parent):
        self.context = context
        self.parent = parent

    @property
    def http_url(self):
        """Return the webapp URL for the context `LibraryFileAlias`.

        Preserve the `LibraryFileAlias.http_url` behavior for deleted
        files, returning None.

        Mask webservice requests if it's the case, so the returned URL will
        be always relative to the parent webapp URL.
        """
        if self.context.deleted:
            return None

        request = get_current_browser_request()
        if WebServiceLayer.providedBy(request):
            request = IWebBrowserOriginatingRequest(request)

        parent_url = canonical_url(self.parent, request=request)
        traversal_url = urlappend(parent_url, '+files')
        url = urlappend(
            traversal_url,
            url_path_quote(self.context.filename.encode('utf-8')))
        return url

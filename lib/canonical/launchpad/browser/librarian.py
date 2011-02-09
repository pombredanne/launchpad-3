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
    'SafeStreamOrRedirectLibraryFileAliasView',
    'StreamOrRedirectLibraryFileAliasView',
    'RedirectPerhapsWithTokenLibraryFileAliasView',
    ]

import os
import tempfile
import urllib2

from lazr.delegates import delegates
from zope.interface import implements
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.security.interfaces import Unauthorized

from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.launchpad.layers import WebServiceLayer
from canonical.launchpad.webapp.authorization import check_permission
from lazr.restful.interfaces import IWebBrowserOriginatingRequest
from canonical.launchpad.webapp.publisher import (
    canonical_url,
    LaunchpadView,
    RedirectionView,
    stepthrough,
    )
from canonical.launchpad.webapp.url import urlappend
from canonical.lazr.utils import get_current_browser_request
from canonical.librarian.client import url_path_quote
from canonical.librarian.interfaces import LibrarianServerError
from canonical.librarian.utils import (
    filechunks,
    guess_librarian_encoding,
    )
from lp.services.features import getFeatureFlag


class LibraryFileAliasView(LaunchpadView):
    """View to handle redirection for downloading files by URL.

    Rather than reference downloadable files via the obscure Librarian
    URL, downloadable files can be referenced via the Product Release URL,
    e.g. http://launchpad.net/firefox/1.0./1.0.0/+download/firefox-1.0.0.tgz.
    """

    def initialize(self):
        """Redirect the request to the URL of the file in the Librarian."""
        # Redirect based on the scheme of the request, as set by Apache in the
        # 'X-SCHEME' environment variable, which is mapped to 'HTTP_X_SCHEME.
        # Note that only some requests for librarian files are allowed to come
        # in via http as most are forced to https via Apache redirection.
        request_scheme = self.request.get('HTTP_X_SCHEME')
        if request_scheme == 'http':
            redirect_to = self.context.http_url
        else:
            redirect_to = self.context.getURL()
        self.request.response.redirect(redirect_to)


class LibraryFileAliasMD5View(LaunchpadView):
    """View to show the MD5 digest for a librarian file."""

    def render(self):
        """Return the plain text MD5 signature"""
        self.request.response.setHeader('Content-type', 'text/plain')
        return '%s %s' % (self.context.content.md5, self.context.filename)


class MixedFileAliasView(LaunchpadView):
    """Stream or redirects to `ILibraryFileAlias`.

    If the file is public, it will redirect to the files http url.

    Otherwise if the feature flag publicrestrictedlibrarian is set to 'on'
    this will allocate a token and redirect to the aliases private url.

    Otherwise it will proxy the file in the appserver.

    Once we no longer have any proxy code at all it should be possible to
    consolidate this with LibraryFileAliasView.

    Note that streaming restricted files is a security concern - they show up
    in the launchpad.net domain rather than launchpadlibrarian.net and thus
    we have to take special care about their origin.
    SafeStreamOrRedirectLibraryFileAliasView is used when we do not trust the
    content, otherwise StreamOrRedirectLibraryFileAliasView. We are working
    to remove both of these views entirely, but some transition will be
    needed.

    The context provides a file-like interface - it can be opened and closed
    and read from.
    """
    implements(IBrowserPublisher)

    def getFileContents(self):
        # Reset system proxy setting if it exists. The urllib2 default
        # opener is cached that's why it has to be re-installed after
        # the shell environment changes. Download the library file
        # content into a local temporary file. Finally, restore original
        # proxy-settings and refresh the urllib2 opener.
        # XXX: This is not threadsafe, so two calls at once will collide and
        # can then corrupt the variable. bug=395960
        original_proxy = os.getenv('http_proxy')
        try:
            if original_proxy is not None:
                del os.environ['http_proxy']
                urllib2.install_opener(urllib2.build_opener())
            tmp_file = tempfile.TemporaryFile()
            self.context.open()
            for chunk in filechunks(self.context):
                tmp_file.write(chunk)
            self.context.close()
        finally:
            if original_proxy is not None:
                os.environ['http_proxy'] = original_proxy
                urllib2.install_opener(urllib2.build_opener())
        return tmp_file

    def __call__(self):
        """Streams the contents of the context `ILibraryFileAlias`.

        The file content is downloaded in chunks directly to a
        `tempfile.TemporaryFile` avoiding using large amount of memory.

        The temporary file is returned to the zope publishing machinery as
        documented in lib/zope/publisher/httpresults.txt, after adjusting
        the response 'Content-Type' appropriately.

        This method explicit ignores the local 'http_proxy' settings.
        """
        try:
            tmp_file = self.getFileContents()
        except LibrarianServerError:
            self.request.response.setHeader('Content-Type', 'text/plain')
            self.request.response.setStatus(503)
            return (u'There was a problem fetching the contents of this '
                     'file. Please try again in a few minutes.')

        # XXX: Brad Crittenden 2007-12-05 bug=174204: When encodings are
        # stored as part of a file's metadata this logic will be replaced.
        encoding, mimetype = guess_librarian_encoding(
            self.context.filename, self.context.mimetype)

        self.request.response.setHeader('Content-Encoding', encoding)
        self.request.response.setHeader('Content-Type', mimetype)
        return tmp_file

    def browserDefault(self, request):
        """Decides how to deliver the file.

        The options are:
         - redirect to the contexts http url
         - redirect to a time limited secure url
         - stream the file content.

        Only restricted file contents are streamed, finishing the traversal
        chain with this view. If the context file is public return the
        appropriate `RedirectionView` for its HTTP url.
        """
        # Perhaps we should give a 404 at this point rather than asserting?
        # If someone has a page open with an attachment link, then someone
        # else deletes the attachment, this is a normal situation, not an
        # error. -- RBC 20100726.
        assert not self.context.deleted, (
            "MixedFileAliasView can not operate on deleted librarian files, "
            "since their URL is undefined.")
        if not self.context.restricted:
            # Public file, just point the client at the right place.
            return RedirectionView(self.context.http_url, self.request), ()
        if getFeatureFlag(u'publicrestrictedlibrarian') != 'on':
            # Restricted file and we have not enabled the public
            # restricted librarian yet :- deliver inline.
            self._when_streaming()
            return self, ()
        # Avoids a circular import seen in
        # scripts/ftests/librarianformatter.txt
        from canonical.launchpad.database.librarian import TimeLimitedToken
        # Allocate a token for the file to be accessed for a limited time and
        # redirect the client to the file.
        token = TimeLimitedToken.allocate(self.context.private_url)
        final_url = self.context.private_url + '?token=%s' % token
        return RedirectionView(final_url, self.request), ()

    def publishTraverse(self, request, name):
        """See `IBrowserPublisher` - can't traverse below a file."""
        raise NotFound(name, self.context)

    def _when_streaming(self):
        """Hook for SafeStreamOrRedirectLibraryFileAliasView."""


class SafeStreamOrRedirectLibraryFileAliasView(MixedFileAliasView):
    """A view for Librarian files that sets the content disposition header."""

    def _when_streaming(self):
        super(
            SafeStreamOrRedirectLibraryFileAliasView, self)._when_streaming()
        self.request.response.setHeader(
            'Content-Disposition', 'attachment')


# The eventual name of MixedFileAliasView once the proxy code
# is ripped out.
RedirectPerhapsWithTokenLibraryFileAliasView = MixedFileAliasView
# The name for the old behaviour being removed:
StreamOrRedirectLibraryFileAliasView = MixedFileAliasView


class DeletedProxiedLibraryFileAlias(NotFound):
    """Raised when a deleted `ProxiedLibraryFileAlias` is accessed."""


class FileNavigationMixin:
    """Navigate to `LibraryFileAlias` hosted in a context.

    The navigation goes through +files/<filename> where file reference is
    provided by context `getFileByName(filename)`.

    The requested file is proxied via `StreamOrRedirectLibraryFileAliasView`,
    making it possible to serve both, public and restricted, files.

    This navigation approach only supports domains with unique filenames,
    which is the case of IArchive and IBuild. It will probably have to be
    extended in order to allow traversing to multiple files potentially
    with the same filename (product files or bug attachments).
    """
    view_class = StreamOrRedirectLibraryFileAliasView

    @stepthrough('+files')
    def traverse_files(self, filename):
        """Traverse on filename in the archive domain."""
        if not check_permission('launchpad.View', self.context):
            raise Unauthorized()
        library_file = self.context.getFileByName(filename)

        # Deleted library files result in NotFound-like error.
        if library_file.deleted:
            raise DeletedProxiedLibraryFileAlias(filename, self.context)

        return self.view_class(library_file, self.request)


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

# (c) Canonical Ltd. 2007, all rights reserved.

__metaclass__ = type

__all__ = [
    'ExportedFolder',
    ]

import errno
import os
import re

from zope.interface import implements

from zope.app.content_types import guess_content_type
from zope.app.datetimeutils import rfc1123_date
from zope.app.publisher.browser.fileresource import setCacheControl
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.publisher.interfaces import NotFound


class File:
    # Copied from zope.app.publisher.fileresource, which
    # unbelievably throws away the file data, and isn't
    # useful extensible.
    #
    def __init__(self, path, name):
        self.path = path

        f = open(path, 'rb')
        self.data = f.read()
        f.close()
        self.content_type, enc = guess_content_type(path, self.data)
        self.__name__ = name
        self.lmt = float(os.path.getmtime(path)) or time()
        self.lmh = rfc1123_date(self.lmt)


class ExportedFolder:
    """View that gives access to the files in a folder.

    The URL to the folder can start with an optional path step like
    /revNNN/ where NNN is one or more digits.  This path step will
    be ignored.  It is useful for having a different path for
    all resources being served, to ensure that we don't use cached
    files in browsers.
    """

    implements(IBrowserPublisher)

    rev_part_re = re.compile('rev\d+$')

    def __init__(self, context, request):
        """Initialize with context and request."""
        self.context = context
        self.request = request
        self.names = []

    def __call__(self):
        names = list(self.names)
        if names and self.rev_part_re.match(names[0]):
            # We have a /revNNN/ path step, so remove it.
            names = names[1:]

        if not names:
            # Just the icing directory, so make this a 404.
            raise NotFound(self, '')
        elif len(names) > 1:
            # Too many path elements, so make this a 404.
            raise NotFound(self, self.names[-1])
        else:
            # Actually serve up the resource.
            [name] = names
            return self.prepareDataForServing(name)

    def prepareDataForServing(self, name):
        """Set the response headers and return the data for this resource."""
        if os.path.sep in name:
            raise ValueError(
                'os.path.sep appeared in the resource name: %s' % name)
        filename = os.path.join(self.here, self.folder, name)
        try:
            fileobj = File(filename, name)
        except IOError, ioerror:
            if ioerror.errno == errno.ENOENT: # No such file or directory
                raise NotFound(self, name)
            else:
                # Some other IOError that we're not expecting.
                raise

        # TODO: Set an appropriate charset too.  There may be zope code we
        #       can reuse for this.
        response = self.request.response
        response.setHeader('Content-Type', fileobj.content_type)
        response.setHeader('Last-Modified', fileobj.lmh)
        setCacheControl(response)
        return fileobj.data

    # The following two zope methods publishTraverse and browserDefault
    # allow this view class to take control of traversal from this point
    # onwards.  Traversed names just end up in self.names.

    def publishTraverse(self, request, name):
        """Traverse to the given name."""
        self.names.append(name)
        return self

    def browserDefault(self, request):
        return self, ()

    @property
    def folder(self):
        raise (
            NotImplementedError,
            'Your subclass of ExportedFolder should have its own folder.')

    @property
    def here(self):
        raise (
            NotImplementedError,
            'Your subclass of ExportedFolder should define its location.')


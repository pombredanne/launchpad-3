# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
#

__metaclass__ = type

import sqlobject

from twisted.web import resource, static, error, util, server, proxy
from twisted.internet.threads import deferToThread

from canonical.librarian.client import quote
from canonical.database.sqlbase import begin, rollback

defaultResource = static.Data(
    'Copyright 2004-2005 Canonical Ltd.\n'
    'These are not the droids you are looking for.\n'
    'kthxbye.\n', type='text/plain')
fourOhFour = error.NoResource('No such resource')

class NotFound(Exception):
    pass


class LibraryFileResource(resource.Resource):
    def __init__(self, storage, upstreamHost, upstreamPort):
        resource.Resource.__init__(self)
        self.storage = storage
        self.upstreamHost = upstreamHost
        self.upstreamPort = upstreamPort

    def getChild(self, name, request):
        if name == '':
            # Root resource
            return defaultResource
        try:
            fileID = int(name)
        except ValueError:
            return fourOhFour
            
        return LibraryFileAliasResource(self.storage, fileID, self.upstreamHost,
                self.upstreamPort)


class LibraryFileAliasResource(resource.Resource):
    def __init__(self, storage, fileID, upstreamHost, upstreamPort):
        resource.Resource.__init__(self)
        self.storage = storage
        self.fileID = fileID
        self.upstreamHost = upstreamHost
        self.upstreamPort = upstreamPort

    def getChild(self, name, request):
        try:
            aliasID = int(name)
        except ValueError:
            return fourOhFour
        if len(request.postpath) != 1:
            return fourOhFour
        filename = request.postpath[0]

        deferred = deferToThread(self._getFileAlias, aliasID)
        deferred.addCallback(self._cb_getFileAlias, aliasID, filename, request)
        deferred.addErrback(self._eb_getFileAlias)
        return util.DeferredResource(deferred)

    def _getFileAlias(self, aliasID):
        begin()
        try:
            try:
                alias = self.storage.getFileAlias(aliasID)
                return alias.contentID, alias.filename, alias.mimetype
            except LookupError:
                raise NotFound
        finally:
            rollback()

    def _eb_getFileAlias(self, failure):
        failure.trap(NotFound)
        return fourOhFour
        
    def _cb_getFileAlias(
            self, (dbcontentID, dbfilename, mimetype),
            aliasID, filename, request
            ):
        # Return a 404 if the filename in the URL is incorrect. This offers
        # a crude form of access control (stuff we care about can have
        # unguessable names effectivly using the filename as a secret).
        if dbfilename.encode('utf-8') != filename:
            return fourOhFour
        # Return a 404 if the contentid in the URL is incorrect. This doesn't
        # gain us much I guess.
        if dbcontentID != self.fileID:
            return fourOhFour
        if self.storage.hasFile(self.fileID) or self.upstreamHost is None:
            return File(mimetype.encode('ascii'),
                        self.storage._fileLocation(self.fileID))
        else:
            return proxy.ReverseProxyResource(self.upstreamHost,
                                              self.upstreamPort, request.path)

    def render_GET(self, request):
        return defaultResource.render(request)


class File(static.File):
    isLeaf = True
    def __init__(self, contentType, *args, **kwargs):
        static.File.__init__(self, *args, **kwargs)
        self.type = contentType
        self.encoding = None


class DigestSearchResource(resource.Resource):
    def __init__(self, storage):
        self.storage = storage

    def render_GET(self, request):
        try:
            digest = request.args['digest'][0]
        except LookupError:
            return static.Data('Bad search', 'text/plain').render(request)

        deferred = deferToThread(self._matchingAliases, digest)
        deferred.addCallback(self._cb_matchingAliases, request)
        deferred.addErrback(_eb, request)
        return server.NOT_DONE_YET

    def _matchingAliases(self, digest):
        begin()
        try:
            library = self.storage.library
            matches = ['%s/%s/%s' % (fID, aID, quote(aName))
                       for fID in library.lookupBySHA1(digest)
                       for aID, aName, aType in library.getAliases(fID)]
            return matches
        finally:
            rollback()

    def _cb_matchingAliases(self, matches, request):
        text = '\n'.join([str(len(matches))] + matches)
        response = static.Data(text.encode('utf-8'),
                               'text/plain; charset=utf-8').render(request)
        request.write(response)
        request.finish()


# Ask robots not to index or archive anything in the librarian.
robotsTxt = static.Data("""
User-agent: *
Disallow: /
""", type='text/plain')


def _eb(failure, request):
    """Generic errback for failures during a render_GET."""
    request.processingFailed(failure)


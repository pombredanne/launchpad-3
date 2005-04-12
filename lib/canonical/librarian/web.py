# Copyright 2004 Canonical Ltd.  All rights reserved.
#

import sqlobject

from twisted.web import resource, static, error, util, server
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
    def __init__(self, storage):
        resource.Resource.__init__(self)
        self.storage = storage

    def getChild(self, name, request):
        if name == '':
            # Root resource
            return defaultResource
        try:
            fileID = int(name)
        except ValueError:
            return fourOhFour
            
        return LibraryFileAliasResource(self.storage, fileID)


class LibraryFileAliasResource(resource.Resource):
    def __init__(self, storage, fileID):
        resource.Resource.__init__(self)
        self.storage = storage
        self.fileID = fileID

    def getChild(self, name, request):
        try:
            aliasID = int(name)
        except ValueError:
            return fourOhFour
        if len(request.postpath) != 1:
            return fourOhFour
        filename = request.postpath[0]

        deferred = deferToThread(self._getFileAlias, filename)
        deferred.addCallback(self._cb_getFileAlias, aliasID)
        deferred.addErrback(self._eb_getFileAlias)
        return util.DeferredResource(deferred)

    def _getFileAlias(self, filename):
        begin()
        try:
            try:
                alias = self.storage.getFileAlias(self.fileID, filename) 
                return alias.id, alias.mimetype
            except IndexError:
                raise NotFound
        finally:
            rollback()

    def _eb_getFileAlias(self, failure):
        failure.trap(NotFound)
        return fourOhFour
        
    def _cb_getFileAlias(self, (dbAliasID, mimetype), aliasID):
        if dbAliasID != aliasID:
            return fourOhFour
        return File(mimetype.encode('ascii'),
                    self.storage._fileLocation(self.fileID))

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


class AliasSearchErrors:
    BAD_SEARCH = 'Bad search'
    NOT_FOUND = 'Not found'

class AliasSearchResource(resource.Resource):
    def __init__(self,storage):
        self.storage = storage

    def render_GET(self, request):
        try:
            alias = int(request.args['alias'][0])
        except (LookupError, ValueError):
            return static.Data(AliasSearchErrors.BAD_SEARCH, 
                               'text/plain').render(request)

        deferred = deferToThread(self._getByAlias, alias)
        deferred.addCallback(self._cb_getByAlias, alias, request)
        deferred.addErrback(self._eb_getByAlias, request)
        deferred.addErrback(_eb, request)
        return server.NOT_DONE_YET

    def _getByAlias(self, alias):
        begin()
        try:
            alias = self.storage.library.getByAlias(alias)
            contentID = alias.content.id
            filename = alias.filename
            return contentID, filename
        finally:
            rollback()

    def _eb_getByAlias(self, failure, request):
        failure.trap(sqlobject.SQLObjectNotFound)
        response = static.Data(AliasSearchErrors.NOT_FOUND,
                               'text/plain').render(request)
        request.write(response)
        request.finish()

    def _cb_getByAlias(self, (contentID, filename), alias, request):
        # Desired format is fileid/aliasid/filename
        ret = "/%s/%s/%s\n" % (contentID, alias, quote(filename))
        response = static.Data(ret.encode('utf-8'), 
                               'text/plain; charset=utf-8').render(request)
        request.write(response)
        request.finish()


def _eb(failure, request):
    """Generic errback for failures during a render_GET."""
    request.processingFailed(failure)


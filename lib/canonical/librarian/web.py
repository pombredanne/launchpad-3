# Copyright 2004 Canonical Ltd.  All rights reserved.
#

from twisted.web import resource, static, error

from canonical.librarian.client import quote

defaultResource = static.Data('Copyright 2004 Canonical Ltd.', type='text/plain')
fourOhFour = error.NoResource('No such resource') 

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
        print 'LibraryFileAliasResource.getChild', repr(name)
        try:
            aliasID = int(name)
        except ValueError:
            return fourOhFour
        print 'aliasID:', aliasID
        print request.postpath
        if len(request.postpath) != 1:
            return fourOhFour
        filename = request.postpath[0]
        print 'filename:', filename
        try:
            alias = self.storage.getFileAlias(self.fileID, filename)
        except IndexError:
            return fourOhFour
        if alias.id != aliasID:
            return fourOhFour
        print self.storage._fileLocation(self.fileID)
        return File(alias.mimetype.encode('ascii'),
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

        library = self.storage.library
        matches = ['%s/%s/%s' % (fID, aID, quote(aName))
                   for fID in library.lookupBySHA1(digest)
                   for aID, aName, aType in library.getAliases(fID)]

        text = '\n'.join(map(str, [len(matches)] + matches))
        return static.Data(text.encode('utf-8'), 'text/plain; charset=utf-8').render(request)
    
class AliasSearchResource(resource.Resource):
    def __init__(self,storage):
        self.storage = storage

    def render_GET(self, request):
        try:
            alias = request.args['alias'][0]
        except LookupError:
            return static.Data('Bad search', 'text/plain').render(request)

        library = self.storage.library
        
        row = library.getByAlias(alias)

        # Desired format is fileid/aliasid/filename
        ret = "/%s/%s/%s\n" % (row.content.id, alias, row.filename)
        return static.Data(ret.encode('utf-8'),
                           'text/plain; charset=utf-8').render(request)


# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# Librarian class is the Librarian wrapper that provides local file cache

# XXX malcc 2006-08-03 bug=55031:
# This looks bogus; looks like it's not used, and assumptions about
# librarian URLs made here (and provided by the testing mocks) no longer
# hold for the real librarian.
# Can this whole file and its tests be squashed?

from canonical.librarian.client import FileDownloadClient
from canonical.librarian.client import FileUploadClient

import os

class Librarian (object):

    def __init__(self, host, upload_port, download_port, cache):
        self.librarian_host = host
        self.upload_port = upload_port
        self.download_port = download_port
        self.cache_path = cache
        if not os.access(cache, os.F_OK):
            os.mkdir(cache)


    def addFile(self, name, size, fileobj, contentType, digest=None,
                cache=True, uploader=None):
        """
        Add a file to the librarian with optional LOCAL CACHE handy
        optimisation same parameters of original addFile and an optional
        cache

        :param cache: Optional boolean in order to allow local cache of File
        :param uploader: Optional FileUploadClient instance (usefull for test)
        """
        if not uploader:
            uploader = FileUploadClient()

        uploader.connect(self.librarian_host, self.upload_port)

        fileid, filealias = uploader.addFile(name, size, fileobj,
                                             contentType, digest)

        if cache:
            ## return to start of the file
            fileobj.seek(0,0)
            self.cacheFile(fileid, filealias, name, fileobj)

        return fileid, filealias

    def downloadFileToDisk(self, aliasID, archive, downloader=None):
        """
        Download a file from Librarian to our LOCAL CACHE and link to
        a given file name (major work for publishing in our archive)

        :param aliasID: Librarian aliasID
        :param filename: resulted file (/cache/<aliasID> should be linked
                         to filename)
        :param downloader: Optional FileDownloadClient instance (useful for
                           testing process)

        """
        if not downloader:
            downloader = FileDownloadClient(self.librarian_host,
                                            self.download_port)

        path = downloader.getPathForAlias(aliasID)

        # XXX: cprov 2004-11-22:
        # The URL returned from Librarian must be correct
        # first '/' results in garbage x !!!
        x, fileid, filealias, name = path.split('/')

        ## Verify if the file is already cached
        if not self.isCached(path):
            ## Grab file from Librarian
            fp = downloader.getFileByAlias(aliasID)

            ## Cache it
            self.cacheFile(fileid, filealias, name, fp)

        ##Link the cached file to the archive anyway, ensure it !!
        path = os.path.join(self.cache_path, fileid, filealias, name)
        self.linkFile(path, archive)


    def cacheFile(self, fileid, filealias, name, fileobj):
        ## efective creation of a file in fielsystem
        # Don't spam the test runner please
        #print 'Caching file', name
        path = os.path.join(self.cache_path, fileid)
        if not os.access(path, os.F_OK):
            os.mkdir(path)
        path = os.path.join(path, filealias)
        if not os.access(path, os.F_OK):
            os.mkdir(path)
        filename = os.path.join(path, name)
        cache = open(filename, "w")
        content = fileobj.read()
        cache.write(content)
        cache.close()


    def isCached(self, path):
        filename = os.path.join(self.cache_path, path)
        return os.access(filename, os.F_OK)

    def linkFile(self, path, archive):
        if os.path.exists(archive):
            os.unlink(archive)
        return os.link(path, archive)

if __name__ == '__main__':
    import os, sys, sha

    lib = Librarian('localhost', 9090, 8000, "/tmp/cache")

    name = sys.argv[1]
    archive = sys.argv[2]

    print 'Uploading', name, 'to %s:%s' %(lib.librarian_host,
                                          lib.upload_port)
    fileobj = open(name, 'rb')
    size = os.stat(name).st_size
    digest = sha.sha(open(name, 'rb').read()).hexdigest()

    fileid, filealias = lib.addFile(name, size, fileobj,
                                    contentType='test/test',
                                    digest=digest)

    print 'Done.  File ID:',  fileid
    print 'File AliasID:', filealias

    lib.downloadFileToDisk(filealias, archive)

    fp = open(archive, 'r')
    print 'First 50 bytes:'
    print repr(fp.read(50))




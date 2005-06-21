#!/usr/bin/env python

# Copyright 2004 Canonical Ltd.  All rights reserved.
#

import unittest
import sys
import os
import shutil
import sha

from canonical.archivepublisher.tests.util import FakeDownloadClient, FakeUploadClient

from canonical.archivepublisher.tests import datadir

class TestLibrarianWrapper(unittest.TestCase):

    def setUp(self):
        ## Create archive and cache dir ...
        os.mkdir(datadir('archive'))
        os.mkdir(datadir('cache'))
                
    def tearDown(self):
        shutil.rmtree(datadir('archive'))
        shutil.rmtree(datadir('cache'))

    def testImport(self):
        """canonical.archivepublisher.Librarian should be importable"""
        from canonical.archivepublisher import Librarian

    def testInstatiate(self):
        """canonical.archivepublisher.Librarian should be instantiatable"""
        from canonical.archivepublisher import Librarian
        lib = Librarian('localhost', 9090, 8000, datadir('cache'))

    def testUpload(self):
        """canonical.archivepublisher.Librarian Upload"""
        name = 'ed_0.2-20.dsc'
        path = datadir(name)

        from canonical.archivepublisher import Librarian
        lib = Librarian('localhost', 9090, 8000, datadir('cache'))

        fileobj = open(path, 'rb')
        size = os.stat(path).st_size
        digest = sha.sha(open(path, 'rb').read()).hexdigest()

        ## Use Fake Librarian class 
        uploader = FakeUploadClient()
        
        fileid, filealias = lib.addFile(name, size, fileobj,
                                        contentType='test/test',
                                        digest=digest,
                                        uploader=uploader)
        #print 'ID %s ALIAS %s' %(fileid, filealias)

        cached = os.path.join(datadir('cache'), name)
        os.path.exists(cached)

    def testDownload(self):
        """canonical.archivepublisher.Librarian DownloadToDisk process"""
        filealias = '1'
        archive = os.path.join (datadir('archive'), 'test')

        from canonical.archivepublisher import Librarian
        lib = Librarian('localhost', 9090, 8000, datadir('cache'))
        ## Use Fake Librarian Class 
        downloader = FakeDownloadClient()

        lib.downloadFileToDisk(filealias, archive, downloader=downloader)

        os.path.exists(archive)


def test_suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestLibrarianWrapper))
    return suite

def main(argv):
    failed = False 
    suite = test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    if not runner.run(suite).wasSuccessful():
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))


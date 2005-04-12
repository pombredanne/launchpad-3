# Copyright 2005 Canonical Ltd.  All rights reserved.

import os
import sha
import sys
import time
import unittest
from cStringIO import StringIO

from twisted.python.util import sibpath

from canonical.launchpad.ftests.harness import LaunchpadTestSetup
from canonical.librarian.client \
        import FileUploadClient, FileDownloadClient, DownloadFailed
from canonical.librarian.ftests.harness import LibrarianTestSetup


class LibraryWebTestCase(unittest.TestCase):
    """Test the librarian's web interface."""

    # Add stuff to a librarian via the upload port, then check that it's
    # immediately visible on the web interface. (in an attempt to test ddaa's
    # 500-error issue).

    def setUp(self):
        LaunchpadTestSetup().setUp()
        LibrarianTestSetup().setUp()

    def tearDown(self):
        LibrarianTestSetup().tearDown()
        LaunchpadTestSetup().tearDown()

    def test_uploadThenDownload(self):
        # Create an uploader and a downloader
        uploader = FileUploadClient()
        downloader = FileDownloadClient()

        # Do this 10 times, to try to make sure we get all the threads in the
        # thread pool involved more than once, in case handling the second
        # request is an issue...
        for count in range(10):
            # Upload a file.  This should work without any exceptions being
            # thrown.
            sampleData = 'x' + ('blah' * count)
            fileID, fileAlias = uploader.addFile('sample', len(sampleData),
                                                 StringIO(sampleData),
                                                 contentType='text/plain')
            
            # Search for the file, make sure it's in there
            path = downloader.getPathForAlias(fileAlias)

            # And search by digest, to make sure that works
            self.assertEqual(
                [(fileID, fileAlias, 'sample')],
                downloader.findByDigest(sha.sha(sampleData).hexdigest())
            )

            # Make sure it can be downloaded, too
            fileObj = downloader.getFile(fileID, fileAlias, 'sample')
            self.assertEqual(sampleData, fileObj.read())
            fileObj.close()

    def test_aliasNotFound(self):
        downloader = FileDownloadClient()
        self.assertRaises(DownloadFailed, downloader.getPathForAlias, 99)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(LibraryWebTestCase))
    return suite


# Copyright 2005 Canonical Ltd.  All rights reserved.

import os
import sha
import sys
import time
import unittest
from cStringIO import StringIO
from urllib import urlopen

from twisted.python.util import sibpath

from canonical.launchpad.ftests.harness import LaunchpadTestSetup
from canonical.librarian.client \
        import DownloadFailed, LibrarianClient
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
        client = LibrarianClient()

        # Do this 10 times, to try to make sure we get all the threads in the
        # thread pool involved more than once, in case handling the second
        # request is an issue...
        for count in range(10):
            # Upload a file.  This should work without any exceptions being
            # thrown.
            sampleData = 'x' + ('blah' * count)
            fileAlias = client.addFile('sample', len(sampleData),
                                                 StringIO(sampleData),
                                                 contentType='text/plain')

            # Make sure we can get its URL and it is usable
            url = client.getURLForAlias(fileAlias)
            sucked_in = urlopen(url).read()
            self.assertEqual(sampleData, sucked_in)

            # Make sure we can download it using the API
            fileObj = client.getFileByAlias(fileAlias)
            self.assertEqual(sampleData, fileObj.read())
            fileObj.close()

class DeprecatedLibraryWebTestCase(unittest.TestCase):
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
        client = LibrarianClient()

        # Do this 10 times, to try to make sure we get all the threads in the
        # thread pool involved more than once, in case handling the second
        # request is an issue...
        for count in range(10):
            # Upload a file.  This should work without any exceptions being
            # thrown.
            sampleData = 'x' + ('blah' * count)
            fileAlias = client.addFile('sample', len(sampleData),
                                                 StringIO(sampleData),
                                                 contentType='text/plain')
            
            # Search for the file, make sure it's in there
            path = client.getPathForAlias(fileAlias)

            # And search by digest, to make sure that works
            r = client.findByDigest(sha.sha(sampleData).hexdigest())
            self.assertEqual(len(r), 1)
            self.assertEqual(len(r[0]), 3,
                'findByDigest returned %r, breaking contract' % (r,))
            self.assertEqual(str(fileAlias), r[0][1])
            self.assertEqual('sample', r[0][2])

            # Make sure it can be downloaded, too
            fileID = r[0][0]
            fileObj = client.getFile(fileID, fileAlias, 'sample')
            self.assertEqual(sampleData, fileObj.read())
            fileObj.close()

    def test_aliasNotFound(self):
        client = LibrarianClient()
        self.assertRaises(DownloadFailed, client.getURLForAlias, 99)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(LibraryWebTestCase))
    return suite


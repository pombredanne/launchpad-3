# Copyright 2005 Canonical Ltd.  All rights reserved.

import os
import sha
import sys
import time
import unittest
from cStringIO import StringIO

from twisted.python.util import sibpath

from canonical.launchpad.ftests.harness import LaunchpadTestCase
from canonical.librarian.client import FileUploadClient, FileDownloadClient


class LibraryWebTestCase(LaunchpadTestCase):
    """Test the librarian's web interface."""

    # Add stuff to a librarian via the upload port, then check that it's
    # immediately visible on the web interface. (in an attempt to test ddaa's
    # 500-error issue).

    def setUp(self):
        super(LibraryWebTestCase, self).setUp()
        # XXX: twistd test-fu taken from authserver/ftests/test_xmlrpc.py
        #      It should be refactored and put somewhere reusable.
        #         - Andrew Bennetts, 2005-02-08
        ver = sys.version[:3]
        os.system('kill `cat twistd.pid 2> /dev/null` > /dev/null 2>&1')
        cmd = 'twistd%s -oy %s' % (ver, sibpath(__file__, 'test.tac'),)
        rv = os.system(cmd)
        self.failUnlessEqual(rv, 0)

        self.uploadPort = waitForTwistdPort('upload')
        self.webPort = waitForTwistdPort('web')

    def tearDown(self):
        # XXX: twistd test-fu taken from authserver/ftests/test_xmlrpc.py
        #      It should be refactored and put somewhere reusable.  (i.e. just
        #      like setUp)
        #         - Andrew Bennetts, 2005-02-08
        pid = int(open('twistd.pid').read())
        ret = os.system('kill `cat twistd.pid`')
        # Wait for it to actually die
        while True:
            try:
                os.kill(pid, 0)
            except OSError:
                break
            time.sleep(0.1)
        os.remove('twistd.log')
        self.failIf(ret)
        super(LibraryWebTestCase, self).tearDown()

    def test_uploadThenDownload(self):
        # Create an uploader and a downloader
        uploader = FileUploadClient()
        uploader.connect('localhost', self.uploadPort)
        downloader = FileDownloadClient('localhost', self.webPort)

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
        downloader = FileDownloadClient('localhost', self.webPort)
        # XXX: Should be a more specific exception
        self.assertRaises(Exception, downloader.getPathForAlias, 99)


def waitForTwistdPort(filePrefix):
    """Wait for the server to be listening on a port, and find out what that
    port is."""

    while True:
        try:
            # Make sure it's really ready, including having written the port
            # to a file
            open(filePrefix + '.ready')

            # Get the file with the port number
            f = open(filePrefix + '.port')
        except IOError:
            pass
        else:
            return int(f.read())

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(LibraryWebTestCase))
    return suite


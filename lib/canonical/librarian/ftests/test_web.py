# Copyright 2005 Canonical Ltd.  All rights reserved.

import unittest
from cStringIO import StringIO
from urllib2 import urlopen, HTTPError

import transaction

from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestSetup
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestSetup
from canonical.librarian.ftests.harness import LibrarianTestSetup
from canonical.librarian.client import LibrarianClient
from canonical.librarian.interfaces import DownloadFailed
from canonical.launchpad.database import LibraryFileAlias
from canonical.config import config
from canonical.database.sqlbase import commit

class LibrarianWebTestCase(unittest.TestCase):
    """Test the librarian's web interface."""

    # Add stuff to a librarian via the upload port, then check that it's
    # immediately visible on the web interface. (in an attempt to test ddaa's
    # 500-error issue).

    def setUp(self):
        LaunchpadFunctionalTestSetup().setUp()
        LibrarianTestSetup().setUp()

    def tearDown(self):
        LibrarianTestSetup().tearDown()
        LaunchpadFunctionalTestSetup().tearDown()

    def commit(self):
        transaction.commit()

    def test_uploadThenDownload(self):
        client = LibrarianClient()

        # Do this 10 times, to try to make sure we get all the threads in the
        # thread pool involved more than once, in case handling the second
        # request is an issue...
        for count in range(10):
            # Upload a file.  This should work without any exceptions being
            # thrown.
            sampleData = 'x' + ('blah' * (count%5))
            fileAlias = client.addFile('sample', len(sampleData),
                                                 StringIO(sampleData),
                                                 contentType='text/plain')

            # Make sure we can get its URL
            url = client.getURLForAlias(fileAlias)

            # However, we can't access it until we have committed,
            # because the server has no idea what mime-type to send it as
            # (NB. This could be worked around if necessary by having the
            # librarian allow access to files that don't exist in the DB
            # and spitting them out with an 'unknown' mime-type-- StuartBishop)
            try:
                urlopen(url)
                self.fail('Should have raised a 404')
            except HTTPError, x:
                self.failUnlessEqual(x.code, 404)

            self.commit()

            # Make sure we can download it using the API
            fileObj = client.getFileByAlias(fileAlias)
            self.assertEqual(sampleData, fileObj.read())
            fileObj.close()

            # And make sure the URL works too
            fileObj = urlopen(url)
            self.assertEqual(sampleData, fileObj.read())
            fileObj.close()

    def test_aliasNotFound(self):
        client = LibrarianClient()
        self.assertRaises(DownloadFailed, client.getURLForAlias, 99)

    def test_oldurl(self):
        # 'old' urls are in the form of http://server:port/cid/aid/fname
        # which we want to continue supporting. The content id is simply
        # ignored
        client = LibrarianClient()
        filename = 'sample.txt'
        aid = client.addFile(filename, 6, StringIO('sample'), 'text/plain')
        self.commit()
        url = client.getURLForAlias(aid)
        self.assertEqual(urlopen(url).read(), 'sample')

        old_url = 'http://%s:%d/42/%d/%s' % (
                config.librarian.download_host,
                config.librarian.download_port,
                aid, filename
                )
        self.assertEqual(urlopen(old_url).read(), 'sample')

        # If the content id is not an integer, a 404 is raised
        old_url = 'http://%s:%d/foo/%d/%s' % (
                config.librarian.download_host,
                config.librarian.download_port,
                aid, filename
                )
        try:
            urlopen(self._makeURL(aid, 'different.txt'))
            self.fail('404 not raised')
        except HTTPError, x:
            self.failUnlessEqual(x.code, 404)

    def _makeURL(self, aliasID, filename):
        host = config.librarian.download_host
        port = config.librarian.download_port
        return 'http://%s:%d/%d/%s' % (
                host, port, aliasID, filename)

    def test_404(self):
        client = LibrarianClient()
        filename = 'sample.txt'
        aid = client.addFile(filename, 6, StringIO('sample'), 'text/plain')
        self.commit()
        url = client.getURLForAlias(aid)
        self.assertEqual(urlopen(url).read(), 'sample')

        # Ensure our helper is working
        self.failUnlessEqual(url, self._makeURL(aid, filename))

        # Change the aliasid and assert we get a 404
        try:
            urlopen(self._makeURL(aid+1, filename))
            self.fail('404 not raised')
        except HTTPError, x:
            self.failUnlessEqual(x.code, 404)

        # Change the filename and assert we get a 404
        try:
            urlopen(self._makeURL(aid, 'different.txt'))
            self.fail('404 not raised')
        except HTTPError, x:
            self.failUnlessEqual(x.code, 404)

    def test_duplicateuploads(self):
        client = LibrarianClient()
        filename = 'sample.txt'
        id1 = client.addFile(filename, 6, StringIO('sample'), 'text/plain')
        id2 = client.addFile(filename, 6, StringIO('sample'), 'text/plain')

        self.failIfEqual(id1, id2, 'Got allocated the same id!')

        self.commit()

        self.failUnlessEqual(client.getFileByAlias(id1).read(), 'sample')
        self.failUnlessEqual(client.getFileByAlias(id2).read(), 'sample')
                    
    def test_robotsTxt(self):
        url = 'http://%s:%d/robots.txt' % (
            config.librarian.download_host, config.librarian.download_port)
        f = urlopen(url)
        self.failUnless('Disallow: /' in f.read())
        
        

class LibrarianZopelessWebTestCase(LibrarianWebTestCase):
    def setUp(self):
        LaunchpadZopelessTestSetup().setUp()
        LibrarianTestSetup().setUp()

    def tearDown(self):
        LibrarianTestSetup().tearDown()
        LaunchpadZopelessTestSetup().tearDown()

    def commit(self):
        commit()

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(LibrarianWebTestCase))
    suite.addTest(unittest.makeSuite(LibrarianZopelessWebTestCase))
    return suite


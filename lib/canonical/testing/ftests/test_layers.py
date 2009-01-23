# Copyright 2006 Canonical Ltd.  All rights reserved.
""" Test layers

Note that many tests are performed at run time in the layers themselves
to confirm that the environment hasn't been corrupted by tests
"""
__metaclass__ = type

import os
import signal
import smtplib
import unittest

from cStringIO import StringIO
from urllib import urlopen
import psycopg2

from zope.component import getUtility, ComponentLookupError

from canonical.config import config, dbconfig
from canonical.launchpad.ftests.harness import LaunchpadTestSetup
from lazr.config import as_host_port
from canonical.librarian.client import LibrarianClient, UploadFailed
from canonical.librarian.interfaces import ILibrarianClient
from canonical.lazr.pidfile import pidfile_path
from canonical.testing.layers import (
    AppServerLayer, BaseLayer, DatabaseLayer, FunctionalLayer,
    LaunchpadFunctionalLayer, LaunchpadLayer, LaunchpadScriptLayer,
    LaunchpadZopelessLayer, LayerInvariantError, LayerIsolationError,
    LayerProcessController, LibrarianLayer, ZopelessLayer)


class BaseTestCase(unittest.TestCase):
    """Both the Base layer tests, as well as the base Test Case
    for all the other Layer tests.
    """
    layer = BaseLayer

    # These flags will be overridden in subclasses to describe the
    # environment they expect to have available.
    want_component_architecture = False
    want_librarian_running = False
    want_launchpad_database = False
    want_functional_flag = False
    want_zopeless_flag = False

    def testBaseIsSetUpFlag(self):
        self.failUnlessEqual(BaseLayer.isSetUp, True)

    def testFunctionalIsSetUp(self):
        self.failUnlessEqual(
                FunctionalLayer.isSetUp, self.want_functional_flag
                )

    def testZopelessIsSetUp(self):
        self.failUnlessEqual(
                ZopelessLayer.isSetUp, self.want_zopeless_flag
                )

    def testComponentArchitecture(self):
        try:
            getUtility(ILibrarianClient)
        except ComponentLookupError:
            self.failIf(
                    self.want_component_architecture,
                    'Component Architecture should be available.'
                    )
        else:
            self.failUnless(
                    self.want_component_architecture,
                    'Component Architecture should not be available.'
                    )

    def testLibrarianRunning(self):
        # Check that the librarian is running. Note that even if the
        # librarian is running, it may not be able to actually store
        # or retrieve files if, for example, the Launchpad database is
        # not currently available.
        try:
            urlopen(config.librarian.download_url).read()
            self.failUnless(
                    self.want_librarian_running,
                    'Librarian should not be running.'
                    )
        except IOError:
            self.failIf(
                    self.want_librarian_running,
                    'Librarian should be running.'
                    )

    def testLibrarianWorking(self):
        # Check that the librian is actually working. This means at
        # a minimum the Librarian service is running and is connected
        # to the Launchpad database.
        want_librarian_working = (
                self.want_librarian_running and self.want_launchpad_database
                and self.want_component_architecture
                )
        client = LibrarianClient()
        data = 'Whatever'
        try:
            file_alias_id = client.addFile(
                    'foo.txt', len(data), StringIO(data), 'text/plain'
                    )
        except UploadFailed:
            self.failIf(
                    want_librarian_working,
                    'Librarian should be fully operational'
                    )
        except (AttributeError, ComponentLookupError):
            self.failIf(
                    want_librarian_working,
                    'Librarian not operational as component architecture '
                    'not loaded'
                    )
        else:
            self.failUnless(
                    want_librarian_working,
                    'Librarian should not be operational'
                    )

    def testLaunchpadDbAvailable(self):
        try:
            con = DatabaseLayer.connect()
            cur = con.cursor()
            cur.execute("SELECT id FROM Person LIMIT 1")
            if cur.fetchone() is not None:
                self.failUnless(
                        self.want_launchpad_database,
                        'Launchpad database should not be available.'
                        )
                return
        except psycopg2.Error:
            pass
        self.failIf(
                self.want_launchpad_database,
                'Launchpad database should be available but is not.'
                )


class LibrarianTestCase(BaseTestCase):
    layer = LibrarianLayer

    want_librarian_running = True

    def testUploadsFail(self):
        # This layer is not particularly useful by itself, as the Librarian
        # cannot function correctly as there is no database setup.
        # We can test this using remoteAddFile (it does not need the CA
        # loaded)
        client = LibrarianClient()
        data = 'This is a test'
        self.failUnlessRaises(
                UploadFailed, client.remoteAddFile,
                'foo.txt', len(data), StringIO(data), 'text/plain'
                )


class LibrarianNoResetTestCase(unittest.TestCase):
    """Our page tests need to run multple tests without destroying
    the librarian database in between.
    """
    layer = LaunchpadLayer

    sample_data = 'This is a test'

    def testNoReset1(self):
        # Inform the librarian not to reset the library until we say
        # otherwise
        LibrarianLayer._reset_between_tests = False

        # Add a file for testNoReset2. We use remoteAddFile because
        # it does not need the CA loaded to work.
        client = LibrarianClient()
        LibrarianTestCase.url = client.remoteAddFile(
                self.sample_data, len(self.sample_data),
                StringIO(self.sample_data), 'text/plain'
                )
        self.failUnlessEqual(
                urlopen(LibrarianTestCase.url).read(), self.sample_data
                )

    def testNoReset2(self):
        # The file added by testNoReset1 should be there
        self.failUnlessEqual(
                urlopen(LibrarianTestCase.url).read(), self.sample_data
                )
        # Restore this - keeping state is our responsibility
        LibrarianLayer._reset_between_tests = True
        # The database was committed to, but not by this process, so we need
        # to ensure that it is fully torn down and recreated.
        DatabaseLayer.force_dirty_database()

    def testNoReset3(self):
        # The file added by testNoReset1 should be gone
        # XXX: StuartBishop 2006-06-30 Bug=51370:
        # We should get a DownloadFailed exception here.
        data = urlopen(LibrarianTestCase.url).read()
        self.failIfEqual(data, self.sample_data)


class LibrarianHideTestCase(unittest.TestCase):
    layer = LaunchpadLayer

    def testHideLibrarian(self):
        # First perform a successful upload:
        client = LibrarianClient()
        data = 'foo'
        client.remoteAddFile(
            'foo', len(data), StringIO(data), 'text/plain')
        # The database was committed to, but not by this process, so we need
        # to ensure that it is fully torn down and recreated.
        DatabaseLayer.force_dirty_database()

        # Hide the librarian, and show that the upload fails:
        LibrarianLayer.hide()
        self.assertRaises(UploadFailed, client.remoteAddFile,
                          'foo', len(data), StringIO(data), 'text/plain')

        # Reveal the librarian again, allowing uploads:
        LibrarianLayer.reveal()
        client.remoteAddFile(
            'foo', len(data), StringIO(data), 'text/plain')


class DatabaseTestCase(BaseTestCase):
    layer = DatabaseLayer

    want_launchpad_database = True

    def testConnect(self):
        DatabaseLayer.connect()

    def getWikinameCount(self, con):
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM Wikiname")
        num = cur.fetchone()[0]
        return num

    def testNoReset1(self):
        # Ensure that we can switch off database resets between tests
        # if necessary, such as used by the page tests
        DatabaseLayer._reset_between_tests = False
        con = DatabaseLayer.connect()
        cur = con.cursor()
        cur.execute("DELETE FROM Wikiname")
        self.failUnlessEqual(self.getWikinameCount(con), 0)
        con.commit()

    def testNoReset2(self):
        # Wikiname table was emptied by testNoReset1 and should still
        # contain nothing.
        con = DatabaseLayer.connect()
        self.failUnlessEqual(self.getWikinameCount(con), 0)
        # Note we don't need to commit, but we do need to force
        # a reset!
        DatabaseLayer._reset_between_tests = True
        DatabaseLayer.force_dirty_database()

    def testNoReset3(self):
        # Wikiname table should contain data again
        con = DatabaseLayer.connect()
        self.failIfEqual(self.getWikinameCount(con), 0)


class LaunchpadTestCase(BaseTestCase):
    layer = LaunchpadLayer

    want_launchpad_database = True
    want_librarian_running = True


class FunctionalTestCase(BaseTestCase):
    layer = FunctionalLayer

    want_component_architecture = True
    want_functional_flag = True


class ZopelessTestCase(BaseTestCase):
    layer = ZopelessLayer

    want_component_architecture = True
    want_launchpad_database = False
    want_librarian_running = False
    want_zopeless_flag = True


class LaunchpadFunctionalTestCase(BaseTestCase):
    layer = LaunchpadFunctionalLayer

    want_component_architecture = True
    want_launchpad_database = True
    want_librarian_running = True
    want_functional_flag = True


class LaunchpadZopelessTestCase(BaseTestCase):
    layer = LaunchpadZopelessLayer

    want_component_architecture = True
    want_launchpad_database = True
    want_librarian_running = True
    want_zopeless_flag = True


class LaunchpadScriptTestCase(BaseTestCase):
    layer = LaunchpadScriptLayer

    want_component_architecture = True
    want_launchpad_database = True
    want_librarian_running = True
    want_zopeless_flag = True

    def testSwitchDbConfig(self):
        # Test that we can switch database configurations, and that we
        # end up connected as the right user.

        self.assertEqual(dbconfig.dbuser, 'launchpad')
        LaunchpadScriptLayer.switchDbConfig('librarian')
        self.assertEqual(dbconfig.dbuser, 'librarian')

        from canonical.database.sqlbase import cursor
        cur = cursor()
        cur.execute('SELECT current_user;')
        user = cur.fetchone()[0]
        self.assertEqual(user, 'librarian')


class LayerProcessControllerInvariantsTestCase(BaseTestCase):
    layer = AppServerLayer

    want_component_architecture = True
    want_launchpad_database = True
    want_librarian_running = True
    want_functional_flag = True
    want_zopeless_flag = False

    def testAppServerIsAvailable(self):
        # Test that the app server is up and running.
        mainsite = LayerProcessController.appserver_config.vhost.mainsite
        home_page = urlopen(mainsite.rooturl).read()
        self.failUnless(
            'What is Launchpad?' in home_page,
            "Home page couldn't be retrieved:\n%s" % home_page)

    def testSMTPServerIsAvailable(self):
        # Test that the SMTP server is up and running.
        smtpd = smtplib.SMTP()
        host, port = as_host_port(config.mailman.smtp)
        code, message = smtpd.connect(host, port)
        self.assertEqual(code, 220)

    def testStartingAppServerTwiceRaisesInvariantError(self):
        # Starting the appserver twice should raise an exception.
        self.assertRaises(LayerInvariantError,
                          LayerProcessController.startAppServer)

    def testStartingSMTPServerTwiceRaisesInvariantError(self):
        # Starting the SMTP server twice should raise an exception.
        self.assertRaises(LayerInvariantError,
                          LayerProcessController.startSMTPServer)


class LayerProcessControllerTestCase(unittest.TestCase):
    """Tests for the `LayerProcessController`."""
    # We need the database to be set up, no more.
    layer = DatabaseLayer

    def tearDown(self):
        # Stop both servers.  It's okay if they aren't running.
        LayerProcessController.stopSMTPServer()
        LayerProcessController.stopAppServer()

    def test_stopAppServer(self):
        # Test that stopping the app server kills the process and remove the
        # PID file.
        LayerProcessController.startAppServer()
        pid = LayerProcessController.appserver.pid
        pid_file = pidfile_path('launchpad',
                                LayerProcessController.appserver_config)
        LayerProcessController.stopAppServer()
        self.assertRaises(OSError, os.kill, pid, 0)
        self.failIf(os.path.exists(pid_file), "PID file wasn't removed")
        self.failUnless(LayerProcessController.appserver is None,
                        "appserver class attribute wasn't reset")

    def test_postTestInvariants(self):
        # A LayerIsolationError should be raised if the app server dies in the
        # middle of a test.
        LayerProcessController.startAppServer()
        pid = LayerProcessController.appserver.pid
        os.kill(pid, signal.SIGTERM)
        LayerProcessController.appserver.wait()
        self.assertRaises(LayerIsolationError,
                          LayerProcessController.postTestInvariants)

    def test_postTestInvariants_dbIsReset(self):
        # The database should be reset by the test invariants.
        LayerProcessController.startAppServer()
        LayerProcessController.postTestInvariants()
        self.assertEquals(True, LaunchpadTestSetup()._reset_db)


class TestNameTestCase(unittest.TestCase):
    layer = BaseLayer
    def testTestName(self):
        self.failUnlessEqual(
                BaseLayer.test_name,
                "testTestName "
                "(canonical.testing.ftests.test_layers.TestNameTestCase)")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

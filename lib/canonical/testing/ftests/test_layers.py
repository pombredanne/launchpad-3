# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

""" Test layers

Note that many tests are performed at run time in the layers themselves
to confirm that the environment hasn't been corrupted by tests
"""
__metaclass__ = type

from cStringIO import StringIO
import os
import signal
import smtplib
from cStringIO import StringIO
from urllib import urlopen

from fixtures import (
    EnvironmentVariableFixture,
    TestWithFixtures,
    )
import psycopg2
import testtools
from zope.component import getUtility, ComponentLookupError

from canonical.config import config, dbconfig
from lazr.config import as_host_port
from canonical.librarian.client import LibrarianClient, UploadFailed
from canonical.librarian.interfaces import ILibrarianClient
from canonical.lazr.pidfile import pidfile_path
from canonical.testing.layers import (
    AppServerLayer,
    BaseLayer,
    DatabaseLayer,
    FunctionalLayer,
    LaunchpadFunctionalLayer,
    LaunchpadLayer,
    LaunchpadScriptLayer,
    LaunchpadTestSetup,
    LaunchpadZopelessLayer,
    LayerInvariantError,
    LayerIsolationError,
    LayerProcessController,
    LibrarianLayer,
    MemcachedLayer,
    ZopelessLayer,
    )
from lp.services.memcache.client import memcache_client_factory


class TestBaseLayer(testtools.TestCase, TestWithFixtures):

    def test_allocates_LP_TEST_INSTANCE(self):
        self.useFixture(
            EnvironmentVariableFixture('LP_PERSISTENT_TEST_SERVICES'))
        self.useFixture(EnvironmentVariableFixture('LP_TEST_INSTANCE'))
        layer = BaseLayer
        layer.setUp()
        try:
            self.assertEqual(str(os.getpid()), os.environ.get('LP_TEST_INSTANCE'))
        finally:
            layer.tearDown()
        self.assertEqual(None, os.environ.get('LP_TEST_INSTANCE'))

    def test_persist_test_services_disables_LP_TEST_INSTANCE(self):
        self.useFixture(
            EnvironmentVariableFixture('LP_PERSISTENT_TEST_SERVICES', ''))
        self.useFixture(EnvironmentVariableFixture('LP_TEST_INSTANCE'))
        layer = BaseLayer
        layer.setUp()
        try:
            self.assertEqual(None, os.environ.get('LP_TEST_INSTANCE'))
        finally:
            layer.tearDown()
        self.assertEqual(None, os.environ.get('LP_TEST_INSTANCE'))

    def test_generates_unique_config(self):
        config.setInstance('testrunner')
        orig_instance = config.instance_name
        self.useFixture(
            EnvironmentVariableFixture('LP_PERSISTENT_TEST_SERVICES'))
        self.useFixture(EnvironmentVariableFixture('LP_TEST_INSTANCE'))
        self.useFixture(EnvironmentVariableFixture('LPCONFIG'))
        layer = BaseLayer
        layer.setUp()
        try:
            self.assertEqual(
                'testrunner_%s' % os.environ['LP_TEST_INSTANCE'],
                config.instance_name)
        finally:
            layer.tearDown()
        self.assertEqual(orig_instance, config.instance_name)

    def test_generates_unique_config_dirs(self):
        self.useFixture(
            EnvironmentVariableFixture('LP_PERSISTENT_TEST_SERVICES'))
        self.useFixture(EnvironmentVariableFixture('LP_TEST_INSTANCE'))
        self.useFixture(EnvironmentVariableFixture('LPCONFIG'))
        layer = BaseLayer
        layer.setUp()
        try:
            runner_root = 'configs/%s' % config.instance_name
            runner_appserver_root = 'configs/testrunner-appserver_%s' % \
                os.environ['LP_TEST_INSTANCE']
            self.assertTrue(os.path.isfile(
                runner_root + '/launchpad-lazr.conf'))
            self.assertTrue(os.path.isfile(
                runner_appserver_root + '/launchpad-lazr.conf'))
        finally:
            layer.tearDown()
        self.assertFalse(os.path.exists(runner_root))
        self.assertFalse(os.path.exists(runner_appserver_root))


class BaseTestCase(testtools.TestCase):
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
    want_memcached = False

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
        if not self.want_launchpad_database:
            self.assertEqual(None, DatabaseLayer._db_fixture)
            return
        con = DatabaseLayer.connect()
        cur = con.cursor()
        cur.execute("SELECT id FROM Person LIMIT 1")
        self.assertNotEqual(None, cur.fetchone())

    def testMemcachedWorking(self):
        client = MemcachedLayer.client or memcache_client_factory()
        key = "BaseTestCase.testMemcachedWorking"
        client.forget_dead_hosts()
        is_live = client.set(key, "live")
        if self.want_memcached:
            self.assertEqual(
                is_live, True, "memcached not live when it should be.")
        else:
            self.assertEqual(
                is_live, False, "memcached is live but should not be.")


class MemcachedTestCase(BaseTestCase):
    layer = MemcachedLayer
    want_memcached = True


class LibrarianTestCase(BaseTestCase):
    layer = LibrarianLayer

    want_launchpad_database = True
    want_librarian_running = True

    def testUploadsSucceed(self):
        # This layer is able to be used on its own as it depends on
        # DatabaseLayer.
        # We can test this using remoteAddFile (it does not need the CA
        # loaded)
        client = LibrarianClient()
        data = 'This is a test'
        client.remoteAddFile(
            'foo.txt', len(data), StringIO(data), 'text/plain')


class LibrarianNoResetTestCase(testtools.TestCase):
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


class LibrarianHideTestCase(testtools.TestCase):
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

    # XXX: Parallel-fail: because layers are not cleanly integrated with
    # unittest, what should be one test is expressed as three distinct
    # tests here. We need to either write enough glue to push/pop the
    # global state of zope.testing.runner or we need to stop using layers,
    # before these tests will pass in a parallel run. Robert Collins
    # 2010-11-01
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
    want_memcached = True


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
    want_memcached = True


class LaunchpadZopelessTestCase(BaseTestCase):
    layer = LaunchpadZopelessLayer

    want_component_architecture = True
    want_launchpad_database = True
    want_librarian_running = True
    want_zopeless_flag = True
    want_memcached = True


class LaunchpadScriptTestCase(BaseTestCase):
    layer = LaunchpadScriptLayer

    want_component_architecture = True
    want_launchpad_database = True
    want_librarian_running = True
    want_zopeless_flag = True
    want_memcached = True

    def testSwitchDbConfig(self):
        # Test that we can switch database configurations, and that we
        # end up connected as the right user.

        self.assertEqual(dbconfig.dbuser, 'launchpad_main')
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
    want_memcached = True

    def testAppServerIsAvailable(self):
        # Test that the app server is up and running.
        mainsite = LayerProcessController.appserver_config.vhost.mainsite
        home_page = urlopen(mainsite.rooturl).read()
        self.failUnless(
            'Is your project registered yet?' in home_page,
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


class LayerProcessControllerTestCase(testtools.TestCase):
    """Tests for the `LayerProcessController`."""
    # We need the database to be set up, no more.
    layer = DatabaseLayer

    def tearDown(self):
        super(LayerProcessControllerTestCase, self).tearDown()
        # Stop both servers.  It's okay if they aren't running.
        LayerProcessController.stopSMTPServer()
        LayerProcessController.stopAppServer()

    def test_stopAppServer(self):
        # Test that stopping the app server kills the process and remove the
        # PID file.
        LayerProcessController._setConfig()
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
        LayerProcessController._setConfig()
        LayerProcessController.startAppServer()
        pid = LayerProcessController.appserver.pid
        os.kill(pid, signal.SIGTERM)
        LayerProcessController.appserver.wait()
        self.assertRaises(LayerIsolationError,
                          LayerProcessController.postTestInvariants)

    def test_postTestInvariants_dbIsReset(self):
        # The database should be reset by the test invariants.
        LayerProcessController._setConfig()
        LayerProcessController.startAppServer()
        LayerProcessController.postTestInvariants()
        # XXX: Robert Collins 2010-10-17 bug=661967 - this isn't a reset, its
        # a flag that it *needs* a reset, which is actually quite different;
        # the lack of a teardown will leak daabases.
        self.assertEquals(True, LaunchpadTestSetup()._reset_db)


class TestNameTestCase(testtools.TestCase):
    layer = BaseLayer
    def testTestName(self):
        self.failUnlessEqual(
                BaseLayer.test_name,
                "testTestName "
                "(canonical.testing.ftests.test_layers.TestNameTestCase)")

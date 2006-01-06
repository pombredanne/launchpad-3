# Copyright (c) 2005 Canonical Ltd.
# Author: David Allouche <david@allouche.net>

import os
import stat
import shutil
import unittest
import logging

from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import HTTPServer
import socket
import errno

import pybaz as arch
from canonical.launchpad.ftests import harness
from canonical.ftests import pgsql
import CVS
import cscvs.cmds.cache
import cscvs.cmds.totla

from importd import archivemanager
from importd import Job

__all__ = [
    'SandboxHelper',
    'ArchiveManagerHelper',
    'BazTreeHelper',
    'ZopelessHelper',
    'ZopelessTestCase',
    'ArchiveManagerTestCase',
    'BazTreeTestCase',
    'WebserverTestCase',
    ]


class SandboxHelper(object):

    def setUp(self):
        self.here = os.getcwd()
        self.home_dir = os.environ.get('HOME')
        self.sandbox_path = os.path.join(self.here, ',,job_test')
        shutil.rmtree(self.sandbox_path, ignore_errors=True)
        os.mkdir(self.sandbox_path)
        os.chdir(self.sandbox_path)
        os.environ['HOME'] = self.sandbox_path
        arch.set_my_id("John Doe <jdoe@example.com>")

    def tearDown(self):
        os.environ['HOME'] = self.home_dir
        shutil.rmtree(self.sandbox_path, ignore_errors=True)
        os.chdir(self.here)
        del self.here
        del self.home_dir
        del self.sandbox_path

    def mkdir(self, name):
        path = self.path(name)
        os.mkdir(path)

    def path(self, name):
        return os.path.join(self.sandbox_path, name)


class ArchiveManagerJobHelper(object):
    """Job Factory for ArchiveManager test cases."""

    def __init__(self, sandbox_helper):
        self.sandbox_helper = sandbox_helper

    def setUp(self):
        self.sandbox_helper.mkdir('mirrors')

    def tearDown(self):
        pass

    jobType = Job.CopyJob

    def makeJob(self):
        job = self.jobType()
        job.archivename = "importd@example.com"
        job.category = "test"
        job.branchto = "branch"
        job.archversion = "0"
        job.slave_home = self.sandbox_helper.sandbox_path
        job.archive_mirror_dir = self.sandbox_helper.path('mirrors')
        return job


class ArchiveManagerHelper(object):
    """Helper for test cases using ArchiveManager."""

    def __init__(self, job_helper):
        self.sandbox_helper = job_helper.sandbox_helper
        self.job_helper = job_helper

    def setUp(self):
        self.sandbox_helper.mkdir('archives')

    def tearDown(self):
        pass

    def makeArchiveManager(self):
        job = self.job_helper.makeJob()
        return archivemanager.ArchiveManager(job)

    def makeVersion(self):
        job = self.job_helper.makeJob()
        version_name = '%s/%s--%s--%s' % (
            job.archivename, job.category, job.branchto, job.archversion)
        return arch.Version(version_name)


def test_path(name):
    test_dir = os.path.dirname(__file__)
    relpath = os.path.join(test_dir, name)
    return os.path.abspath(relpath)


class BazTreeHelper(object):

    def __init__(self, archive_manager_helper):
        self.archive_manager_helper = archive_manager_helper
        self.sandbox_helper = archive_manager_helper.sandbox_helper
        self.version = None
        self.tree = None

    def setUp(self):
        self.version = self.archive_manager_helper.makeVersion()

    def setUpSigning(self):
        sandbox_path = self.sandbox_helper.sandbox_path
        gpgdir = self.sandbox_helper.path('gpg')
        os.mkdir(gpgdir)
        private_name = "john.doe@snakeoil.gpg"
        private_path = os.path.join(gpgdir, private_name)
        shutil.copyfile(test_path(private_name), private_path)
        dotgnupg = os.path.join(sandbox_path, '.gnupg')
        os.mkdir(dotgnupg)
        os.chmod(dotgnupg, stat.S_IRWXU)
        keyring_name = "pubring.gpg"
        keyring_path = os.path.join(dotgnupg, keyring_name)
        shutil.copyfile(test_path(keyring_name), keyring_path)
        defaults_path = os.path.join(
            sandbox_path, '.arch-params', 'archives', 'defaults')
        defaults = open(defaults_path, 'w')
        print >> defaults, (
            "gpg_options=--no-default-keyring"
            + " --secret-keyring " + private_path
            + " --default-key john.doe@snakeoil")
        defaults.close()

    def tearDown(self):
        self.tree = None

    def setUpTree(self):
        assert self.tree is None
        sandbox_path = self.sandbox_helper.sandbox_path
        path = self.sandbox_helper.path('tree')
        os.mkdir(path)
        self.tree = arch.init_tree(path, self.version, nested=True)

    def cleanUpTree(self):
        shutil.rmtree(str(self.tree))
        self.version.get(str(self.tree))

    def setUpBaseZero(self):
        self.tree.import_()

    def setUpPatch(self):
        msg = self.tree.log_message()
        msg['Summary'] = 'revision'
        self.tree.commit(msg)


class CscvsJobHelper(ArchiveManagerJobHelper):
    """Job factory for CVSStrategy test cases."""

    def setUp(self):
        ArchiveManagerJobHelper.setUp(self)
        self.cvsroot = self.sandbox_helper.path('cvsrepo')
        self.cvsmodule = 'test'

    def makeJob(self):
        job = ArchiveManagerJobHelper.makeJob(self)
        job.RCS = "CVS"
        job.TYPE = "sync"
        job.repository = self.cvsroot
        job.module = self.cvsmodule
        job.branchfrom="MAIN"
        return job


class CscvsHelper(object):
    """Helper for integration tests with CSCVS."""

    def __init__(self, baz_tree_helper):
        self.sandbox_helper = baz_tree_helper.sandbox_helper
        self.archive_manager_helper = baz_tree_helper.archive_manager_helper
        self.job_helper = self.archive_manager_helper.job_helper
        self.baz_tree_helper = baz_tree_helper

    def setUp(self):
        self.cvsroot = self.job_helper.cvsroot
        self.cvsmodule = self.job_helper.cvsmodule
        self.cvstreedir = self.sandbox_helper.path('cvstree')

    def tearDown(self):
        pass

    def writeSourceFile(self, data):
        aFile = open(os.path.join(self.cvstreedir, 'file1'), 'w')
        aFile.write(data)
        aFile.close()

    def setUpCvsToSyncWith(self):
        """Setup a small CVS repository to sync with."""
        repo = CVS.init(self.cvsroot)
        sourcedir = self.cvstreedir
        os.mkdir(sourcedir)
        self.writeSourceFile("import\n")
        repo.Import(module=self.cvsmodule, log="import", vendor="vendor",
                    release=['release'], dir=sourcedir)
        shutil.rmtree(sourcedir)
        repo.get(module=self.cvsmodule, dir=sourcedir)
        self.writeSourceFile("change1\n")
        cvsTree = CVS.tree(sourcedir)
        cvsTree.commit(log="change 1")
        shutil.rmtree(sourcedir)

    def doRevisionOne(self):
        """Import revision 1 from CVS to Bazaar."""
        archive_manager = self.archive_manager_helper.makeArchiveManager()
        archive_manager.createMaster()
        self.baz_tree_helper.setUpSigning()
        self.baz_tree_helper.setUpTree()
        cvsrepo = CVS.Repository(self.cvsroot, logging)
        cvsrepo.get(module="test", dir=self.cvstreedir)
        argv = ["-b"]
        config = CVS.Config(self.cvstreedir)
        config.args = argv
        cscvs.cmds.cache.cache(config, logging, argv)
        config = CVS.Config(self.cvstreedir)
        baz_tree_path = str(self.baz_tree_helper.tree)
        config.args = ["-Si", "1", baz_tree_path]
        cscvs.cmds.totla.totla(config, logging, ["-Si", "1", baz_tree_path])


class ZopelessHelper(harness.LaunchpadZopelessTestSetup):
    dbuser = 'importd'

    # XXX installFakeConnect and uninstallFakeConnect are required to use
    # LaunchpadZopelessTestSetup without the test.py launchpad runner.
    # -- David Allouche 2005-05-11

    def setUp(self):
        pgsql.installFakeConnect()
        harness.LaunchpadZopelessTestSetup.setUp(self)

    def tearDown(self):
        harness.LaunchpadZopelessTestSetup.tearDown(self)
        pgsql.uninstallFakeConnect()


class SandboxTestCase(unittest.TestCase):
    """Base class for test cases that need a SandboxHelper."""

    def setUp(self):
        self.sandbox_helper = SandboxHelper()
        self.sandbox_helper.setUp()

    def tearDown(self):
        self.sandbox_helper.tearDown()


class ArchiveManagerTestCase(unittest.TestCase):
    """A test case that combines SandboxHelper and ArchiveManagerHelper."""

    jobHelperType = ArchiveManagerJobHelper

    def setUp(self):
        self.sandbox_helper = SandboxHelper()
        self.sandbox_helper.setUp()
        self.job_helper = self.jobHelperType(self.sandbox_helper)
        self.job_helper.setUp()
        self.archive_manager_helper = ArchiveManagerHelper(self.job_helper)
        self.archive_manager_helper.setUp()
        self.archive_manager = self.archive_manager_helper.makeArchiveManager()
        self.version = self.archive_manager.version

    def tearDown(self):
        self.archive_manager_helper.tearDown()
        self.job_helper.tearDown()
        self.sandbox_helper.tearDown()

    def masterPatchlevels(self):
        """List of patchlevels in the master branch."""
        master = self.archive_manager._master
        levels = [revision.patchlevel for revision
                  in self.version.iter_location_revisions(master)]
        return levels

    def assertMasterPatchlevels(self, expected):
        """Test that the master branch contains the specified patchlevels.

        A missing master branch is an error.
        """
        levels = self.masterPatchlevels()
        self.assertEqual(levels, expected)

    def mirrorPatchlevels(self):
        """List of patchlevels in the mirror branch."""
        mirror = self.archive_manager._mirror
        levels = [revision.patchlevel for revision
                  in self.version.iter_location_revisions(mirror)]
        return levels

    def assertMirrorPatchlevels(self, expected):
        """Test that the mirror branch contains the specified patchlevels.

        A missing mirror branch is treated the same as empty.
        """
        mirror = self.archive_manager._mirror
        if self.version in self.version.archive.iter_location_versions(mirror):
            levels = self.mirrorPatchlevels()
        else:
            levels = []
        self.assertEqual(levels, expected)

    def mirrorBranch(self):
        """Mirror the branch of the ArchiveManager.""" 
        master = self.archive_manager._master
        mirror = self.archive_manager._mirror
        master.make_mirrorer(mirror).mirror(limit=self.version)


class BazTreeTestCase(ArchiveManagerTestCase):
    """Base class for test cases needing a working tree."""

    def setUp(self):
        ArchiveManagerTestCase.setUp(self)
        self.baz_tree_helper = BazTreeHelper(self.archive_manager_helper)
        self.baz_tree_helper.setUp()

    def tearDown(self):
        self.baz_tree_helper.tearDown()
        ArchiveManagerTestCase.tearDown(self)


class CscvsTestCase(BazTreeTestCase):
    """Base class for tests using cscvs."""

    jobHelperType = CscvsJobHelper

    def setUp(self):
        BazTreeTestCase.setUp(self)
        self.cscvs_helper = CscvsHelper(self.baz_tree_helper)
        self.cscvs_helper.setUp()
        self.job_helper.cvsroot = self.cscvs_helper.cvsroot

    def tearDown(self):
        self.cscvs_helper.tearDown()
        BazTreeTestCase.tearDown(self)


class ZopelessTestCase(unittest.TestCase):
    """Base class for test cases that need database access."""

    def setUp(self):
        self.zopeless_helper = ZopelessHelper()
        self.zopeless_helper.setUp()

    def tearDown(self):
        self.zopeless_helper.tearDown()


# Webserver helper was based on the bzr code for doing http tests.

class WebserverNotAvailable(Exception):
    pass

class BadWebserverPath(ValueError):
    def __str__(self):
        return 'path %s is not in %s' % self.args

class TestHTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

class WebserverHelper(SandboxHelper):

    HTTP_PORTS = range(13000, 0x8000)

    def _http_start(self):
        httpd = None
        for port in self.HTTP_PORTS:
            try:
                httpd = HTTPServer(('localhost', port), TestHTTPRequestHandler)
            except socket.error, e:
                if e.args[0] == errno.EADDRINUSE:
                    continue
                print >>sys.stderr, "Cannot run webserver :-("
                raise
            else:
                break

        if httpd is None:
            raise WebserverNotAvailable("Cannot run webserver :-( "
                                        "no free ports in range %s..%s" %
                                        (self.HTTP_PORTS[0],
                                         self.HTTP_PORTS[-1]))

        self._http_base_url = 'http://localhost:%s/' % port
        self._http_starting.release()
        httpd.socket.settimeout(0.1)

        while self._http_running:
            try:
                httpd.handle_request()
            except socket.timeout:
                pass

    def get_remote_url(self, path):
        import os

        path_parts = path.split(os.path.sep)
        if os.path.isabs(path):
            if path_parts[:len(self._local_path_parts)] != \
                   self._local_path_parts:
                raise BadWebserverPath(path, self.sandbox_path)
            remote_path = '/'.join(path_parts[len(self._local_path_parts):])
        else:
            remote_path = '/'.join(path_parts)

        self._http_starting.acquire()
        self._http_starting.release()
        return self._http_base_url + remote_path

    def setUp(self):
    	SandboxHelper.setUp(self)
        import threading, os
        self._local_path_parts = self.sandbox_path.split(os.path.sep)
        self._http_starting = threading.Lock()
        self._http_starting.acquire()
        self._http_running = True
        self._http_base_url = None
        self._http_thread = threading.Thread(target=self._http_start)
        self._http_thread.setDaemon(True)
        self._http_thread.start()
        self._http_proxy = os.environ.get("http_proxy")
        if self._http_proxy is not None:
            del os.environ["http_proxy"]

    def tearDown(self):
        self._http_running = False
        self._http_thread.join()
        if self._http_proxy is not None:
            import os
            os.environ["http_proxy"] = self._http_proxy
        SandboxHelper.tearDown(self)

class WebserverTestCase(unittest.TestCase):
    """Base class for test cases that need a WebserverHelper."""

    def setUp(self):
        self.zopeless_helper = ZopelessHelper()
        self.zopeless_helper.setUp()
        self.webserver_helper = WebserverHelper()
        self.webserver_helper.setUp()

    def tearDown(self):
        self.webserver_helper.tearDown()
        self.zopeless_helper.tearDown()

    def path(self, name):
        return self.webserver_helper.path(name)

    def url(self, name):
        return self.webserver_helper.get_remote_url(name)


# Copyright (c) 2005 Canonical Ltd.
# Author: David Allouche <david@allouche.net>

import os
import shutil
import unittest

from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import HTTPServer
import socket

from canonical.launchpad.ftests import harness
from canonical.ftests import pgsql

# Boilerplate to get getUtility working.
from canonical.launchpad.interfaces import (
    IBranchSet, ILaunchpadCelebrities, IPersonSet, IProductSet,
    IProductSeriesSet)
from canonical.launchpad.utilities import LaunchpadCelebrities
from canonical.launchpad.database import (
    PersonSet, BranchSet, ProductSet, ProductSeriesSet)
from zope.app.testing.placelesssetup import setUp as zopePlacelessSetUp
from zope.app.testing.placelesssetup import tearDown as zopePlacelessTearDown
from zope.app.testing import ztapi

from importd import Job


__all__ = [
    'SandboxHelper',
    'ZopelessHelper',
    'ZopelessUtilitiesHelper',
    'ZopelessTestCase',
    'JobTestCase',
    'WebserverTestCase',
    ]


class SandboxHelper(object):

    def setUp(self):
        # overriding HOME and clearing EDITOR is part of the standard
        # boilerplate to set up a baz sandbox.
        self.here = os.getcwd()
        self.home_dir = os.environ.get('HOME')
        self.saved_editor = os.environ.get('EDITOR')
        self.path = os.path.join(self.here, ',,job_test')
        shutil.rmtree(self.path, ignore_errors=True)
        os.mkdir(self.path)
        os.chdir(self.path)
        os.environ['HOME'] = self.path
        os.environ.pop('EDITOR', None) # delete 'EDITOR' if present

    def tearDown(self):
        os.environ['HOME'] = self.home_dir
        if self.saved_editor is not None:
            os.environ['EDITOR'] = self.saved_editor
        shutil.rmtree(self.path, ignore_errors=True)
        os.chdir(self.here)

    def mkdir(self, name):
        path = self.join(name)
        os.mkdir(path)

    def join(self, component, *more_components):
        """Join one or more pathname components after the sandbox path."""
        return os.path.join(self.path, component, *more_components)


class SimpleJobHelper(object):
    """Simple job factory."""

    def __init__(self, sandbox):
        self.sandbox = sandbox
        self.series_id = 42

    def setUp(self):
        pass

    def tearDown(self):
        pass

    jobType = Job.CopyJob

    def makeJob(self):
        job = self.jobType()
        job.slave_home = self.sandbox.path
        job.seriesID = self.series_id
        job.push_prefix = self.sandbox.join('bzr-mirrors')
        return job


def test_path(name):
    test_dir = os.path.dirname(__file__)
    relpath = os.path.join(test_dir, name)
    return os.path.abspath(relpath)


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


class ZopelessUtilitiesHelper(object):

    def setUp(self):
        self.zopeless_helper = ZopelessHelper()
        self.zopeless_helper.setUp()
        # Boilerplate to get getUtility working
        zopePlacelessSetUp()
        ztapi.provideUtility(ILaunchpadCelebrities, LaunchpadCelebrities())
        ztapi.provideUtility(IPersonSet, PersonSet())
        ztapi.provideUtility(IBranchSet, BranchSet())
        ztapi.provideUtility(IProductSet, ProductSet())
        ztapi.provideUtility(IProductSeriesSet, ProductSeriesSet())

    def tearDown(self):
        zopePlacelessTearDown()
        self.zopeless_helper.tearDown()


class SandboxTestCase(unittest.TestCase):
    """Base class for test cases that need a SandboxHelper."""

    def setUp(self):
        self.sandbox = SandboxHelper()
        self.sandbox.setUp()

    def tearDown(self):
        self.sandbox.tearDown()


class JobTestCase(unittest.TestCase):
    """A test case that combines SandboxHelper and a job helper."""

    jobHelperType = SimpleJobHelper

    def setUp(self):
        self.sandbox = SandboxHelper()
        self.sandbox.setUp()
        self.job_helper = self.jobHelperType(self.sandbox)
        self.job_helper.setUp()

    def tearDown(self):
        self.job_helper.tearDown()
        self.sandbox.tearDown()


class ZopelessTestCase(unittest.TestCase):
    """Base class for test cases that need database access."""

    def setUp(self):
        self.zopeless_helper = ZopelessHelper()
        self.zopeless_helper.setUp()

    def tearDown(self):
        self.zopeless_helper.tearDown()


# Webserver helper was based on the bzr code for doing http tests.

class BadWebserverPath(ValueError):
    def __str__(self):
        return 'path %s is not in %s' % self.args

class TestHTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class WebserverHelper(SandboxHelper):

    def _http_start(self):
        httpd = HTTPServer(('localhost', 0), TestHTTPRequestHandler)
        host, port = httpd.socket.getsockname()

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
                raise BadWebserverPath(path, self.path)
            remote_path = '/'.join(path_parts[len(self._local_path_parts):])
        else:
            remote_path = '/'.join(path_parts)

        self._http_starting.acquire()
        self._http_starting.release()
        return self._http_base_url + remote_path

    def setUp(self):
        SandboxHelper.setUp(self)
        import threading, os
        self._local_path_parts = self.path.split(os.path.sep)
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

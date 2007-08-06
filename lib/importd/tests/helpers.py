# Copyright (c) 2005 Canonical Ltd.
# Author: David Allouche <david@allouche.net>

import os
import shutil
import unittest

from canonical.launchpad.ftests import harness
from canonical.ftests import pgsql

from importd import Job


__all__ = [
    'SandboxHelper',
    'ZopelessHelper',
    'ZopelessUtilitiesHelper',
    'ZopelessTestCase',
    'JobTestCase',
    ]


class SandboxHelper(object):

    def setUp(self):
        # overriding HOME so bzr won't see user settings
        self.here = os.getcwd()
        self.home_dir = os.environ.get('HOME')
        self.path = os.path.join(self.here, ',,job_test')
        shutil.rmtree(self.path, ignore_errors=True)
        os.mkdir(self.path)
        os.chdir(self.path)
        os.environ['HOME'] = self.path

    def tearDown(self):
        os.environ['HOME'] = self.home_dir
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


class ZopelessHelper(harness.LaunchpadZopelessTestSetup):
    dbuser = 'importd'

    # XXX David Allouche 2005-05-11:
    # installFakeConnect and uninstallFakeConnect are required to use
    # LaunchpadZopelessTestSetup without the test.py launchpad runner.

    def setUp(self):
        pgsql.installFakeConnect()
        harness.LaunchpadZopelessTestSetup.setUp(self)

    def tearDown(self):
        harness.LaunchpadZopelessTestSetup.tearDown(self)
        pgsql.uninstallFakeConnect()


class ZopelessUtilitiesHelper(object):

    # XXX: DavidAllouche 2007-04-27: 
    # This helper used to call zopePlacelessSetup, and set up a few
    # IFooSet utilities. Since we now call execute_zcml_for_scripts from the
    # importd test runner, this is no longer needed, and actually prevented
    # correct operation. Now, this whole class should probably be factored
    # away.

    def setUp(self):
        self.zopeless_helper = ZopelessHelper()
        self.zopeless_helper.setUp()

    def tearDown(self):
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



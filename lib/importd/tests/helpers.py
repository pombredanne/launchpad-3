# Copyright (c) 2005 Canonical Ltd.
# Author: David Allouche <david@allouche.net>

import os
import shutil
import unittest

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



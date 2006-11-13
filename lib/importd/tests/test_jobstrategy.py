# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test cases for JobStrategy functionality that is common to CVS and SVN."""

__metaclass__ = type

import os
import unittest

from importd import JobStrategy
from importd.tests import testutil
from importd.tests.helpers import JobTestCase


class TestCvsStrategyCreation(unittest.TestCase):

    def assertInstanceMethod(self, method, class_, name):
        """Assert that `method` is a specific instance method.

        :param method: this must be an instance method
        :param class_: `method` must be from an instance of this class.
        :param name: `method` must have this name.
        """
        self.assertEqual(method.im_class, class_)
        self.assertEqual(method.im_func.__name__, name)

    def assertCvsStrategyMethod(self, method, name):
        """Assert that method is an instance method from CVSStrategy.

        :param method: this must be a method of a CVSStrategy instance.
        :param name: 'method' must have this name.
        """
        self.assertInstanceMethod(method, JobStrategy.CVSStrategy, name)

    def testGetCvsStrategy(self):
        # Test getting a cvs strategy.
        CVS_import = JobStrategy.get('CVS', 'import')
        self.assertCvsStrategyMethod(CVS_import, 'Import')
        cvs_import = JobStrategy.get('cvs', 'import')
        self.assertCvsStrategyMethod(cvs_import, 'Import')
        CVS_sync = JobStrategy.get('CVS', 'sync')
        self.assertCvsStrategyMethod(CVS_sync, 'sync')
        cvs_sync = JobStrategy.get('cvs', 'sync')
        self.assertCvsStrategyMethod(cvs_sync, 'sync')

    def assertSvnStrategyMethod(self, method, name):
        """Assert that method is an instance method from SVNStrategy.

        :param method: this must be a method of a SVNStrategy instance.
        :param name: 'method' must have this name.
        """
        self.assertInstanceMethod(method, JobStrategy.SVNStrategy, name)

    def testGetSvnStrategy(self):
        # Test getting a svn strategy.
        SVN_import = JobStrategy.get('SVN', 'import')
        self.assertSvnStrategyMethod(SVN_import, 'Import')
        svn_import = JobStrategy.get('svn', 'import')
        self.assertSvnStrategyMethod(svn_import, 'Import')
        SVN_sync = JobStrategy.get('SVN', 'sync')
        self.assertSvnStrategyMethod(SVN_sync, 'sync')
        svn_sync = JobStrategy.get('svn', 'sync')
        self.assertSvnStrategyMethod(svn_sync, 'sync')

    def testGetInvalidRCS(self):
        # Test getting a strategy with an invalid RCS name.
        self.assertRaises(KeyError, JobStrategy.get, "blargh", "sync")

    def testGetInvalidType(self):
        # Test getting a strategy with an invalid job type.
        self.assertRaises(KeyError, JobStrategy.get, "CVS", "blargh")


class TestCscvsStrategy(JobTestCase):
    """Test cases for CSCVSStrategy."""

    def testGetWorkingDir(self):
        # test that the working dir is calculated & created correctly
        strategy = JobStrategy.CSCVSStrategy()
        job = self.job_helper.makeJob()
        working_dir = strategy.getWorkingDir(job, self.sandbox.path)
        expected_working_dir = self.sandbox.join('series-0000002a')
        self.assertEqual(working_dir, expected_working_dir)
        self.failUnless(os.path.exists(working_dir))


testutil.register(__name__)

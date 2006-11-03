# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test cases for JobStrategy functionality that is common to CVS and SVN."""

__metaclass__ = type

import unittest

from importd import JobStrategy
from importd.tests import testutil


class TestCvsStrategyCreation(unittest.TestCase):

    def assertInstanceMethod(self, method, class_, name):
        self.assertEqual(method.im_class, class_)
        self.assertEqual(method.im_func.__name__, name)

    def testGet(self):
        """Test getting a Strategy"""
        CVS_import = JobStrategy.get("CVS", "import")
        self.assertInstanceMethod(CVS_import, JobStrategy.CVSStrategy, 'Import')
        cvs_import = JobStrategy.get("cvs", "import")
        self.assertInstanceMethod(cvs_import, JobStrategy.CVSStrategy, 'Import')
        CVS_sync = JobStrategy.get("CVS", "sync")
        self.assertInstanceMethod(CVS_sync, JobStrategy.CVSStrategy, 'sync')
        cvs_sync = JobStrategy.get("cvs", "sync")
        self.assertInstanceMethod(cvs_sync, JobStrategy.CVSStrategy, 'sync')

    def testGetInvalidRCS(self):
        """Test getting with invalid RCS"""
        self.assertRaises(KeyError, JobStrategy.get, "blargh", "sync")

    def testGetInvalidType(self):
        """Test getting with invalid type"""
        self.assertRaises(KeyError, JobStrategy.get, "CVS", "blargh")


testutil.register(__name__)

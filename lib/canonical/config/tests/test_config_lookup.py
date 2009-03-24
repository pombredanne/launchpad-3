# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test our mechanisms for locating which config file to use."""

__metaclass__ = type
__all__ = []

import os
from tempfile import NamedTemporaryFile
from unittest import makeSuite, TestCase, TestSuite

from canonical import config

class TestConfigLookup(TestCase):

    def setUp(self):
        self.temp_lookup_file = None
        self.original_CONFIG_LOOKUP_FILES = config.CONFIG_LOOKUP_FILES
        self.original_LPCONFIG = os.environ['LPCONFIG']

    def tearDown(self):
        del self.temp_lookup_file
        config.CONFIG_LOOKUP_FILES = self.original_CONFIG_LOOKUP_FILES
        os.environ['LPCONFIG'] = self.original_LPCONFIG

    def makeLookupFile(self):
        self.temp_lookup_file = NamedTemporaryFile()
        self.temp_lookup_file.write('\nfrom_disk \n')
        self.temp_lookup_file.flush()
        config.CONFIG_LOOKUP_FILES = [
            NamedTemporaryFile().name, self.temp_lookup_file.name]

    def testByEnvironment(self):
        # Create the lookup file to demonstrate it is overridden.
        self.makeLookupFile()

        os.environ['LPCONFIG'] = 'from_env'

        self.failUnlessEqual(config.find_instance_name(), 'from_env')

    def testByFile(self):
        # Create the lookup file.
        self.makeLookupFile()

        # Trash the environment variable so it doesn't override.
        del os.environ['LPCONFIG']

        self.failUnlessEqual(config.find_instance_name(), 'from_disk')

    def testByDefault(self):
        # Trash the environment variable so it doesn't override.
        del os.environ['LPCONFIG']

        self.failUnlessEqual(
            config.find_instance_name(), config.DEFAULT_CONFIG)


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(TestConfigLookup))
    return suite

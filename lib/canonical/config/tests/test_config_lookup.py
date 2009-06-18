# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Test our mechanisms for locating which config file to use."""

__metaclass__ = type
__all__ = []

import os
import shutil
from tempfile import mkdtemp, NamedTemporaryFile
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


class TestInstanceConfigDirLookup(TestCase):
    """Test where instance config directories are looked up."""

    def setUp(self):
        self.temp_config_root_dir = mkdtemp('configs')
        self.instance_config_dir = os.path.join(
            self.temp_config_root_dir, 'an_instance')
        os.mkdir(self.instance_config_dir)
        self.original_root_dirs = config.CONFIG_ROOT_DIRS
        config.CONFIG_ROOT_DIRS = [self.temp_config_root_dir]

    def tearDown(self):
        shutil.rmtree(self.temp_config_root_dir)
        config.CONFIG_ROOT_DIRS = self.original_root_dirs

    def test_find_config_dir_raises_ValueError(self):
        self.assertRaises(
            ValueError, config.find_config_dir, 'no_instance')

    def test_find_config_dir(self):
        self.assertEquals(
            self.instance_config_dir, config.find_config_dir('an_instance'))

    def test_Config_uses_find_config_dir(self):
        # Create a very simple config file.
        config_file = open(
            os.path.join(self.instance_config_dir, 'launchpad-lazr.conf'),
            'w')
        config_file.write('[launchpad]\ndefault_batch_size=2323')
        config_file.close()
        cfg = config.CanonicalConfig('an_instance')

        # We don't care about ZConfig...
        cfg._setZConfig = lambda: None
        self.assertEquals(2323, cfg.launchpad.default_batch_size)


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(TestConfigLookup))
    suite.addTest(makeSuite(TestInstanceConfigDirLookup))
    return suite

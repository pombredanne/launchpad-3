# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# We know we are not using root and handlers.
"""Test lp.services.config."""


__metaclass__ = type

from doctest import (
    DocTestSuite,
    ELLIPSIS,
    NORMALIZE_WHITESPACE,
    )
import os
import unittest

from fixtures import TempDir
from lazr.config import ConfigSchema
from lazr.config.interfaces import ConfigErrors
import pkg_resources
import testtools
import ZConfig

import lp.services.config
from lp.services.config.fixture import ConfigUseFixture

# Configs that shouldn't be tested.
EXCLUDED_CONFIGS = ['lpnet-template']

# Calculate some landmark paths.
schema_file = pkg_resources.resource_filename('zope.app.server', 'schema.xml')
schema = ZConfig.loadSchema(schema_file)

here = os.path.dirname(lp.services.config.__file__)
lazr_schema_file = os.path.join(here, 'schema-lazr.conf')


def make_test(config_file, description):
    def test_function():
        root, handlers = ZConfig.loadConfig(schema, config_file)
    # Hack the config file name into test_function's __name__ so that the test
    # -vv output is more informative. Unfortunately, FunctionTestCase's
    # description argument doesn't do what we want.
    test_function.__name__ = description
    return unittest.FunctionTestCase(test_function)


def make_config_test(config_file, description):
    """Return a class to test a single lazr.config file.

    The config file name is shown in the output of test.py -vv. eg.
    (lp.services.config.tests.test_config.../configs/schema.lazr.conf)
    """
    class LAZRConfigTestCase(unittest.TestCase):
        """Test a lazr.config."""
        def testConfig(self):
            """Validate the config against the schema.

            All errors in the config are displayed when it is invalid.
            """
            schema = ConfigSchema(lazr_schema_file)
            config = schema.load(config_file)
            try:
                config.validate()
            except ConfigErrors as error:
                message = '\n'.join([str(e) for e in error.errors])
                self.fail(message)
    # Hack the config file name into the class name.
    LAZRConfigTestCase.__name__ = '../' + description
    return LAZRConfigTestCase


class TestLaunchpadConfig(testtools.TestCase):

    def test_dir(self):
        # dir(config) returns methods, variables and section names.
        config = lp.services.config.config
        names = set(dir(config))
        self.assertTrue(names.issuperset(dir(config.__class__)))
        self.assertTrue(names.issuperset(config.__dict__))
        section_names = set(section.name for section in config._config)
        self.assertTrue(names.issuperset(section_names))

    def test_iter(self):
        # iter(config) returns an iterator of sections.
        config = lp.services.config.config
        # Reload the config if needed: without this call,
        # `config._config` can be None (see bug 987904).
        config._getConfig()
        sections = set(config._config)
        self.assertEqual(sections, set(config))

    def test_override_directory(self):
        # The launchpad.config_overlay_dir setting can be used to load
        # extra config files over the top. This is useful for overlaying
        # non-version-controlled secrets.
        config_dir = self.useFixture(TempDir(rootdir='configs'))
        config_name = os.path.basename(config_dir.path)
        overlay_dir = self.useFixture(TempDir(rootdir='configs'))
        with open(config_dir.join('launchpad-lazr.conf'), 'w') as f:
            f.write("""
                [meta]
                extends: ../testrunner/launchpad-lazr.conf

                [launchpad]
                config_overlay_dir: ../%s
                """ % os.path.basename(overlay_dir.path))
        os.symlink(
            '../testrunner/launchpad.conf', config_dir.join('launchpad.conf'))

        config = lp.services.config.config

        with ConfigUseFixture(config_name):
            self.assertEqual('launchpad_main', config.launchpad.dbuser)
            self.assertEqual('', config.launchpad.site_message)

        with open(overlay_dir.join('00-test-lazr.conf'), 'w') as f:
            f.write("""
                [launchpad]
                dbuser: overlay-user
                site_message: An overlay!
                """)
        with ConfigUseFixture(config_name):
            self.assertEqual('overlay-user', config.launchpad.dbuser)
            self.assertEqual('An overlay!', config.launchpad.site_message)

        with open(overlay_dir.join('01-test-lazr.conf'), 'w') as f:
            f.write("""
                [launchpad]
                site_message: Another overlay!
                """)
        with ConfigUseFixture(config_name):
            self.assertEqual('overlay-user', config.launchpad.dbuser)
            self.assertEqual('Another overlay!', config.launchpad.site_message)

        os.unlink(overlay_dir.join('00-test-lazr.conf'))
        with ConfigUseFixture(config_name):
            self.assertEqual('launchpad_main', config.launchpad.dbuser)
            self.assertEqual('Another overlay!', config.launchpad.site_message)


def test_suite():
    """Return a suite of canonical.conf and all conf files."""
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite(
        'lp.services.config',
        optionflags=NORMALIZE_WHITESPACE | ELLIPSIS,
        ))
    load_testcase = unittest.defaultTestLoader.loadTestsFromTestCase
    # Add a test for every launchpad[.lazr].conf file in our tree.
    for config_dir in lp.services.config.CONFIG_ROOT_DIRS:
        for dirpath, dirnames, filenames in os.walk(config_dir):
            if os.path.basename(dirpath) in EXCLUDED_CONFIGS:
                del dirnames[:]  # Don't look in subdirectories.
                continue
            for filename in filenames:
                if filename == 'launchpad.conf':
                    config_file = os.path.join(dirpath, filename)
                    description = os.path.relpath(config_file, config_dir)
                    suite.addTest(make_test(config_file, description))
                elif filename.endswith('-lazr.conf'):
                    # Test the lazr.config conf files.
                    config_file = os.path.join(dirpath, filename)
                    description = os.path.relpath(config_file, config_dir)
                    testcase = make_config_test(config_file, description)
                    suite.addTest(load_testcase(testcase))
                else:
                    # This file is not a config that can be validated.
                    pass
    # Other tests.
    suite.addTest(load_testcase(TestLaunchpadConfig))
    return suite

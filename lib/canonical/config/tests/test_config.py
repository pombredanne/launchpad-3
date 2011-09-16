# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# We know we are not using root and handlers.
# pylint: disable-msg=W0612

"""Test canonical.config."""


__metaclass__ = type

from doctest import DocTestSuite, NORMALIZE_WHITESPACE, ELLIPSIS
import os
import pkg_resources
import unittest

from lazr.config import ConfigSchema
from lazr.config.interfaces import ConfigErrors
import ZConfig

import canonical.config

# Configs that shouldn't be tested.
EXCLUDED_CONFIGS = ['lpnet-template']

# Calculate some landmark paths.
schema_file = pkg_resources.resource_filename('zope.app.server', 'schema.xml')
schema = ZConfig.loadSchema(schema_file)

here = os.path.dirname(canonical.config.__file__)
lazr_schema_file = os.path.join(here, 'schema-lazr.conf')


def make_test(config_file, description):
    def test_function():
        root, handlers = ZConfig.loadConfig(schema, config_file)
    test_function.__name__ = description
    return test_function


def make_config_test(config_file, description):
    """Return a class to test a single lazr.config file.

    The config file name is shown in the output of test.py -vv. eg.
    (canonical.config.tests.test_config.../configs/schema.lazr.conf)
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
            except ConfigErrors, error:
                message = '\n'.join([str(e) for e in error.errors])
                self.fail(message)
    # Hack the config file name into the class name.
    LAZRConfigTestCase.__name__ = '../' + description
    return LAZRConfigTestCase


class TestCanonicalConfig(unittest.TestCase):

    def test_dir(self):
        # dir(config) returns methods, variables and section names.
        config = canonical.config.config
        names = set(dir(config))
        self.assertTrue(names.issuperset(dir(config.__class__)))
        self.assertTrue(names.issuperset(config.__dict__))
        section_names = set(section.name for section in config._config)
        self.assertTrue(names.issuperset(section_names))

    def test_iter(self):
        # iter(config) returns an iterator of config sections.
        config = canonical.config.config
        self.assertEqual(set(config._config), set(config))


def test_suite():
    """Return a suite of canonical.conf and all conf files."""
    # We know we are not using dirnames.
    # pylint: disable-msg=W0612
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite(
        'canonical.config',
        optionflags=NORMALIZE_WHITESPACE | ELLIPSIS,
        ))
    # Add a test for every launchpad[.lazr].conf file in our tree.
    for config_dir in canonical.config.CONFIG_ROOT_DIRS:
        prefix_len = len(os.path.dirname(config_dir)) + 1
        for dirpath, dirnames, filenames in os.walk(config_dir):
            if os.path.basename(dirpath) in EXCLUDED_CONFIGS:
                continue
            for filename in filenames:
                if filename == 'launchpad.conf':
                    config_file = os.path.join(dirpath, filename)
                    description = config_file[prefix_len:]
                    # Hack the config file name into the test_function's
                    # __name__ # so that the test -vv output is more
                    # informative. Unfortunately, FunctionTestCase's
                    # description argument doesn't do what we want.
                    suite.addTest(unittest.FunctionTestCase(
                        make_test(config_file, description)))
                elif filename.endswith('-lazr.conf'):
                    # Test the lazr.config conf files.
                    config_file = os.path.join(dirpath, filename)
                    description = config_file[prefix_len:]
                    test = make_config_test(config_file, description)
                    suite.addTest(test('testConfig'))
                else:
                    # This file is not a config that can be validated.
                    pass
    # Other tests.
    suite.addTest(
        unittest.defaultTestLoader.loadTestsFromTestCase(
            TestCanonicalConfig))
    return suite

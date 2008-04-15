# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# We know we are not using root and handlers.
# pylint: disable-msg=W0612

"""Test canonical.config."""


__metaclass__ = type

import ZConfig
import os
import unittest

from zope.testing.doctest import DocTestSuite, NORMALIZE_WHITESPACE, ELLIPSIS
from canonical.lazr.config import ConfigSchema
from canonical.lazr.interfaces.config import ConfigErrors


# Calculate some landmark paths.
import canonical.config
here = os.path.dirname(canonical.config.__file__)
schema_file = os.path.join(
    here, os.pardir, os.pardir, 'zope/app/server/schema.xml')
schema = ZConfig.loadSchema(schema_file)

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
    LAZRConfigTestCase.__name__ = '../configs/' + description
    return LAZRConfigTestCase


def test_suite():
    """Return a suite of canonical.conf and all conf files."""
    # We know we are not using dirnames.
    # pylint: disable-msg=W0612
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite(
        'canonical.config',
        optionflags=NORMALIZE_WHITESPACE | ELLIPSIS
        ))
    # Add a test for every launchpad[.lazr].conf file in our tree.
    top_directory = os.path.join(here, '../../..', 'configs')
    prefix_len = len(top_directory) + 1
    for dirpath, dirnames, filenames in os.walk(top_directory):
        for filename in filenames:
            if filename == 'launchpad.conf':
                config_file = os.path.join(dirpath, filename)
                description = config_file[prefix_len:]
                # Hack the config file name into the test_function's __name__
                # so that the test -vv output is more informative.
                # Unfortunately, FunctionTestCase's description argument
                # doesn't do what we want.
                suite.addTest(unittest.FunctionTestCase(
                    make_test(config_file, 'configs/' + description)))
            elif filename.endswith('-lazr.conf'):
                # Test the lazr.config conf files.
                config_file = os.path.join(dirpath, filename)
                description = config_file[prefix_len:]
                test = make_config_test(config_file, description)
                suite.addTest(test('testConfig'))
            else:
                # This file is not a config that can be validated.
                pass
    return suite



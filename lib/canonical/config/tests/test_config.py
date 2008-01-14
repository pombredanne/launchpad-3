# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import ZConfig
import os
import unittest

from zope.testing.doctest import DocTestSuite, NORMALIZE_WHITESPACE, ELLIPSIS

# Calculate some landmark paths.
import canonical.config
here = os.path.dirname(canonical.config.__file__)
schema_file = os.path.join(here, 'schema.xml')
schema = ZConfig.loadSchema(schema_file)

# This is necessary because pid_dir typically points to a directory that only
# exists on the deployed servers, almost never on a developer machine.
overrides = ['canonical/pid_dir=/tmp']


def make_test(config_file, description):
    def test_function():
        root, handlers = ZConfig.loadConfig(schema, config_file, overrides)
    test_function.__name__ = description
    return test_function


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite(
        'canonical.config',
        optionflags=NORMALIZE_WHITESPACE | ELLIPSIS
        ))
    # Add a test for every launchpad.conf file in our tree.
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
                
    return suite



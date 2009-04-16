# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Support code for using a custom test result in test.py."""

__metaclass__ = type
__all__ = [
    'patch_zope_testresult',
    ]

from unittest import TestSuite
from testtools import MultiTestResult, iterate_tests
from zope.testing import testrunner


class Anything:

    def __getattr__(self, name):
        return lambda *args, **kwargs: None



def patch_find_tests(hook):
    """Add a post-processing hook to zope.testing.testrunner.find_tests."""
    real_find_tests = testrunner.find_tests
    def find_tests(*args):
        return hook(real_find_tests(*args))
    testrunner.find_tests = find_tests


def list_tests(tests_by_layer_name):
    for suite in tests_by_layer_name.itervalues():
        for test in iterate_tests(suite):
            print test.id()
    return {}


def filter_tests(list_name):
    def do_filter(tests_by_layer_name):
        tests = sorted(set(line.strip() for line in open(list_name, 'rb')))
        result = {}
        for layer_name, suite in tests_by_layer_name.iteritems():
            new_suite = TestSuite()
            for test in iterate_tests(suite):
                if test.id() in tests:
                    new_suite.addTest(test)
            if new_suite.countTestCases():
                result[layer_name] = new_suite
        return result
    return do_filter


def patch_zope_testresult(result):
    """Patch the Zope test result factory so that our test result is used.

    We need to keep using the Zope test result object since it does all sorts
    of crazy things to make layers work. So that the output of our result
    object is used, we disable the output of the Zope test result object.

    :param result: A TestResult instance.
    """
    old_zope_factory = testrunner.TestResult
    def zope_result_factory(options, tests, layer_name=None):
        zope_result = old_zope_factory(options, tests, layer_name=layer_name)
        if isinstance(zope_result, MultiTestResult):
            return zope_result
        else:
            zope_result.options.output = Anything()
            return MultiTestResult(result, zope_result)
    testrunner.TestResult = zope_result_factory

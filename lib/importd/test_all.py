#!/usr/bin/env python
# Copyright 2006 Canonical Ltd.  All rights reserved.
# Authors: Robert Collins <robert.collins@canonical.com>
#          David Allouche <david.allouche@canonical.com>

"""Runner for the importd test suite

This is present for historical reasons, as importd used to live in the buildbot
tree. Eventually, that should go away and importd should use the launchpad test
runner.
"""

__metaclass__ = type


import os
import sys
import unittest

from importd.tests.testutil import TestVisitor, TestSuite


# XXX 2006-05-08 Andrew Bennetts:
#    Same nasty hack as in test.py in the root directory of launchpad, more or
#    less.  We need to remove the launchpad root directory from sys.path, so
#    that zope.testbrowser can "from test import pystone".  Otherwise, it finds
#    our test.py script instead.
lp_root = os.path.realpath(os.path.join(__file__, '..', '..', '..'))
sys.path[:] = [p for p in sys.path if os.path.abspath(p) != lp_root]


class ParameterisableTextTestRunner(unittest.TextTestRunner):
    """I am a TextTestRunner whose result class is 
    parameterisable without further subclassing"""
    def __init__(self, **args):
        unittest.TextTestRunner.__init__(self, **args)
        self._resultFactory=None
    def resultFactory(self, *args):
        """set or retrieve the result factory"""
        if args:
            self._resultFactory=args[0]
            return self
        if self._resultFactory is None:
            self._resultFactory=unittest._TextTestResult
        return self._resultFactory
        
    def _makeResult(self):
        return self.resultFactory()(self.stream, self.descriptions, self.verbosity)

    
class EarlyStoppingTextTestResult(unittest._TextTestResult):
    """I am a TextTestResult that can optionally stop at the first failure
    or error"""
    
    def addError(self, test, err):
        unittest._TextTestResult.addError(self, test, err)
        if self.stopOnError():
            self.stop()

    def addFailure(self, test, err):
        unittest._TextTestResult.addError(self, test, err)
        if self.stopOnFailure():
            self.stop()

    def stopOnError(self, *args):
        """should this result indicate an abort when an error occurs?
        TODO parameterise this"""
        return False
    
    def stopOnFailure(self, *args):
        """should this result indicate an abort when a failure error occurs?
        TODO parameterise this"""
        return False


def earlyStopFactory(*args, **kwargs):
    """return a an early stopping text test result"""
    result=EarlyStoppingTextTestResult(*args, **kwargs)
    return result
    

def test_suite():
    result=TestSuite()
    import tests
    result.addTest(tests.test_suite())
    return result


class filteringVisitor(TestVisitor):
    """I accruse all the testCases I visit that pass a regexp filter on id
    into my suite"""
    def __init__(self, filter):
        import re
        TestVisitor.__init__(self)
        self._suite=None
        self.filter=re.compile(filter)
    def suite(self):
        """answer the suite we are building"""
        if self._suite is None:
            self._suite=TestSuite()
        return self._suite
    def visitCase(self, aCase):
        if self.filter.match(aCase.id()):
            self.suite().addTest(aCase)


def main(argv):
    """To parameterise what tests are run, run this script like so:
    python test_all.py REGEX
    i.e.
    python test_all.py .*Protocol.*
    to run all tests with Protocol in their id."""
    if len(argv) > 1:
        pattern=argv[1]
    else:
        pattern=".*"
    visitor=filteringVisitor(pattern)
    test_suite().visit(visitor)
    runner=ParameterisableTextTestRunner(verbosity=2).resultFactory(earlyStopFactory)
    if not runner.run(visitor.suite()).wasSuccessful(): return 1
    return 0

 
if __name__ == '__main__':
    sys.exit(main(sys.argv))

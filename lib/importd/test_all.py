#!/usr/bin/python2.4
# -*- Mode: python -*-
#
# Copyright (C) 2004-2006 Canonical.com 
#       Author:      Robert Collins <robert.collins@canonical.com>
#
# -----------------------------------------------------------------------
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. 
# -----------------------------------------------------------------------
#

"""Runner for the importd test suite

This is present for historical reasons, as importd used to live in the buildbot
tree. Eventually, that should go away and importd should use the launchpad test
runner.
"""

__metaclass__ = type


import os
import sys
import unittest

# XXX 2006-05-08 Andrew Bennetts:
#    Same nasty hack as in test.py in the root directory of launchpad, more or
#    less.  We need to remove the launchpad root directory from sys.path, so
#    that zope.testbrowser can "from test import pystone".  Otherwise, it finds
#    our test.py script instead.
lp_root = os.path.realpath(os.path.join(__file__, '..', '..', '..'))
sys.path[:] = [p for p in sys.path if os.path.abspath(p) != lp_root]

from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.testing.layers import is_ca_available
from importd.tests.testutil import TestVisitor, TestSuite


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
        if self.filter.search(aCase.id()):
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

    # XXX: DavidAllouche 2007-04-27: 
    # jobsFromSeries uses canonical_url. This requires the zope component
    # architecture to be set up. Since the CA cannot be tore down, and this
    # test runner does not know about layers (and does not know to run tests
    # that do not require the CA before it is setup), we run
    # execute_zcml_for_scripts in the initialization of the test runner.
    execute_zcml_for_scripts()
    assert is_ca_available(), (
        "Component architecture not loaded by execute_zcml_for_scripts")

    if not runner.run(visitor.suite()).wasSuccessful(): return 1
    return 0

 
if __name__ == '__main__':
    sys.exit(main(sys.argv))

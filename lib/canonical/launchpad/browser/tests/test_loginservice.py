# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test harness for Login Service related unit tests."""

__metaclass__ = type

__all__ = []

import unittest

from canonical.functional import FunctionalDocFileSuite
from canonical.launchpad.ftests.test_system_documentation import (
    default_optionflags, setUp, tearDown)
from canonical.testing import LaunchpadFunctionalLayer

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(FunctionalDocFileSuite('loginservice.txt',
                  optionflags=default_optionflags, package=__name__,
                  setUp=setUp, tearDown=tearDown,
                  layer=LaunchpadFunctionalLayer))
    return suite

if __name__ == '__main__':
    unittest.main()


# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test harness for running the logintoken-corner-cases.txt tests."""

__metaclass__ = type

import unittest

from canonical.functional import FunctionalDocFileSuite
from canonical.launchpad.ftests.test_system_documentation import (
    default_optionflags, setUp, tearDown)
from canonical.testing import LaunchpadFunctionalLayer


def test_suite():
    suite = unittest.TestSuite()

    test = FunctionalDocFileSuite('logintoken-corner-cases.txt',
        setUp=setUp, tearDown=tearDown,
        optionflags=default_optionflags,
        package=__name__,
        layer=LaunchpadFunctionalLayer)
    suite.addTest(test)
    return suite

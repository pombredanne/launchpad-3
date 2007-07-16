# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Tests for the validators."""

__metaclass__ = type

import unittest

from canonical.functional import FunctionalDocFileSuite
from canonical.testing.layers import LaunchpadFunctionalLayer
from canonical.launchpad.ftests.test_system_documentation import (
    default_optionflags, setUp, tearDown)


def test_suite():
    suite = unittest.TestSuite()
    test = FunctionalDocFileSuite(
        'validation.txt', setUp=setUp, tearDown=tearDown,
        optionflags=default_optionflags, package=__name__,
        layer=LaunchpadFunctionalLayer)
    suite.addTest(test)
    return suite


if __name__ == '__main__':
    unittest.main()

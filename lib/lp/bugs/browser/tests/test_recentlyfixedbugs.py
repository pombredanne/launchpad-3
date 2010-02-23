# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test harness for running the recently-fixed-bugs.txt tests."""

__metaclass__ = type

__all__ = []

import unittest

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite


def test_suite():
    suite = unittest.TestSuite()
    test = LayeredDocFileSuite('recently-fixed-bugs.txt')
    suite.addTest(test)
    return suite

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test harness for running the buglinktarget.txt interface test

This module will run the interface test against the CVE, Specification and
Question implementations of that interface.
"""

__metaclass__ = type

__all__ = []

import unittest

from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.systemdocs import (
    LayeredDocFileSuite,
    setUp,
    tearDown,
    )


def test_suite():
    suite = unittest.TestSuite()

    test = LayeredDocFileSuite(
        'decoratedresultset.txt',
        setUp=setUp, tearDown=tearDown,
        layer=DatabaseFunctionalLayer)
    suite.addTest(test)
    return suite


if __name__ == '__main__':
    unittest.main()

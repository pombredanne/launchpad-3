# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test harness for running the decoratedresultset.txt test.

All the non-documentation-worthy tests for the DecoratedResultSet class.
"""

__metaclass__ = type

__all__ = []

import unittest

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.testing.layers import LaunchpadZopelessLayer


def test_suite():
    return LayeredDocFileSuite('decoratedresultset.txt', layer=LaunchpadZopelessLayer)

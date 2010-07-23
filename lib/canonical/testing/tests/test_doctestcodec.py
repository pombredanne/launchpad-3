# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the doctestcodec module."""

__metaclass__ = type
__all__ = []

from doctest import DocTestSuite
import unittest

import canonical.testing.doctestcodec

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(DocTestSuite(canonical.testing.doctestcodec))
    return suite


# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Runn test_logger.txt."""

__metaclass__ = type
__all__ = []

import unittest
from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.testing import BaseLayer

def test_suite():
    return unittest.TestSuite([
        LayeredDocFileSuite(
            'test_logger.txt', layer=BaseLayer),])

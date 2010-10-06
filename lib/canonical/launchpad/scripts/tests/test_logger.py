# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Runn test_logger.txt."""

__metaclass__ = type
__all__ = []

import unittest

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.testing.layers import BaseLayer


def test_suite():
    return unittest.TestSuite([
        LayeredDocFileSuite(
            'test_logger.txt', layer=BaseLayer),])

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for test layers."""

__metaclass__ = type
__all__ = []

import unittest

from canonical.testing.layers import BaseWindmillLayer, DatabaseLayer
from lp.testing import TestCase


class TestBaseWindmillLayer(TestCase):

    layer_to_test = BaseWindmillLayer

    def test_db_reset_between_tests(self):
        # The db is reset between tests when DatabaseLayer layer's
        # testSetUp is called, if _reset_between_tests is True.
        self.assertTrue(
            issubclass(self.layer_to_test, DatabaseLayer))
        self.assertTrue(self.layer_to_test._reset_between_tests)



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

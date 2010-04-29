# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the bulk database functions."""

__metaclass__ = type

import unittest

from lp.services.database import bulk

from lp.testing import TestCase


identity = lambda thing: thing


class TestFunctions(TestCase):

    def test_collate_empty_list(self):
        self.failUnlessEqual([], list(bulk.collate([], identity)))

    def test_collate_with_identity(self):
        self.failUnlessEqual(
            [(1, [1])],
            list(bulk.collate([1], identity)))
        self.failUnlessEqual(
            [(1, [1]), (2, [2, 2])],
            sorted(bulk.collate([1, 2, 2], identity)))

    def test_collate_with_key_function(self):
        self.failUnlessEqual(
            [(4, ['fred', 'joss']), (6, ['barney'])],
            sorted(bulk.collate(['fred', 'barney', 'joss'], len)))




def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

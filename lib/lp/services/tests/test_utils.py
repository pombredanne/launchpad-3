# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type

import itertools
import unittest

from lp.services.utils import CachingIterator, iter_split
from lp.testing import TestCase


class TestIterateSplit(TestCase):
    """Tests for iter_split."""

    def test_iter_split(self):
        # iter_split loops over each way of splitting a string in two using
        # the given splitter.
        self.assertEqual([('one', '')], list(iter_split('one', '/')))
        self.assertEqual([], list(iter_split('', '/')))
        self.assertEqual(
            [('one/two', ''), ('one', 'two')],
            list(iter_split('one/two', '/')))
        self.assertEqual(
            [('one/two/three', ''), ('one/two', 'three'),
             ('one', 'two/three')],
            list(iter_split('one/two/three', '/')))


class TestCachingIterator(TestCase):
    """Tests for CachingIterator."""

    def test_reuse(self):
        # The same iterator can be used multiple times.
        iterator = CachingIterator(itertools.count())
        self.assertEqual(
            [0,1,2,3,4], list(itertools.islice(iterator, 0, 5)))
        self.assertEqual(
            [0,1,2,3,4], list(itertools.islice(iterator, 0, 5)))

    def test_more_values(self):
        # If a subsequent call to iter causes more values to be fetched, they
        # are also cached.
        iterator = CachingIterator(itertools.count())
        self.assertEqual(
            [0,1,2], list(itertools.islice(iterator, 0, 3)))
        self.assertEqual([0,1,2], iterator.data)
        self.assertEqual(
            [0,1,2,3,4], list(itertools.islice(iterator, 0, 5)))
        self.assertEqual([0,1,2,3,4], iterator.data)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

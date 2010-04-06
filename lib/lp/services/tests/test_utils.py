# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type

import unittest

from lp.services.utils import iter_split
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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

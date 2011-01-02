# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the LibrarianServerFixture."""

__metaclass__ = type

import doctest
import unittest

from canonical.librarian.testing.server import LibrarianServerFixture
from lp.testing import TestCase

def test_suite():
    result = unittest.TestLoader().loadTestsFromName(__name__)
    result.addTest(doctest.DocTestSuite(
            'canonical.librarian.testing.server',
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
            ))
    return result


class TestLibrarianServerFixture(TestCase):

    def test_on_init_no_pid(self):
        fixture = LibrarianServerFixture()
        if fixture._persistent_servers():
            self.skip('persistent server running.')
        self.assertEqual(None, fixture.pid)

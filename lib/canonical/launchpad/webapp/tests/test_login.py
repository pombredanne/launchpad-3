# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from canonical.launchpad.ftests import logout
from canonical.launchpad.testing.pages import setupBrowser
from canonical.testing import DatabaseFunctionalLayer

from lp.testing import TestCase


class TestLoginOrRegister_preserve_query(TestCase):
    layer = DatabaseFunctionalLayer

    def test_non_ascii_characters_in_query_string_ascii_encoded(self):
        # Apport can construct ASCII-encoded URLs containing non-ASCII
        # characters (in the query string), where they send users to so that
        # they can finish reporting bugs. Apport shouldn't do that but we
        # can't OOPS when it does, so we use UnicodeDammit to figure out its
        # original encoding and decode it back. If UnicodeDammit can't figure
        # out the correct encoding, we replace those non-ASCII characters. For
        # more details, see https://launchpad.net/bugs/61171.
        logout()
        browser = setupBrowser()
        browser.open('http://launchpad.dev/+login?foo=subproc%E9s')
        self.assertEquals(
            'subproc\xc3\xa9s', browser.getControl(name='foo', index=0).value)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

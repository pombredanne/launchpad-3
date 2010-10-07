# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the person_sort_key stored procedure."""

__metaclass__ = type

import unittest

from canonical.testing.layers import LaunchpadLayer


class TestPersonSortKey(unittest.TestCase):
    layer = LaunchpadLayer

    def setUp(self):
        self.con = self.layer.connect()
        self.cur = self.con.cursor()

    def tearDown(self):
        self.con.close()

    def person_sort_key(self, displayname, name):
        '''Calls the person_sort_key stored procedure

        Note that although the stored procedure returns a UTF-8 encoded
        string, our database driver converts that to Unicode for us.
        '''
        self.cur.execute(
                "SELECT person_sort_key(%(displayname)s, %(name)s)", vars()
                )
        return self.cur.fetchone()[0]

    def test_person_sort_key(self):

        # person_sort_key returns the concatenation of the display name
        # and the name for use in sorting.
        self.failUnlessEqual(
                self.person_sort_key("Stuart Bishop", "stub"),
                "stuart bishop, stub"
                )

        # Leading and trailing whitespace is removed
        self.failUnlessEqual(
                self.person_sort_key(" Stuart Bishop\t", "stub"),
                "stuart bishop, stub"
                )

        # 'name' is assumed to be lowercase and not containing anything
        # we don't want. This should never happen as the valid_name database
        # constraint should prevent it.
        self.failUnlessEqual(
                self.person_sort_key("Stuart Bishop", " stub42!!!"),
                "stuart bishop,  stub42!!!"
                )

        # Everything except for letters and whitespace is stripped.
        self.failUnlessEqual(
                self.person_sort_key("-= Mass1v3 T0SSA =-", "tossa"),
                "massv tssa, tossa"
                )

        # Non ASCII letters are currently allowed. Eventually they should
        # become transliterated to ASCII but we don't do this yet.
        # Note that as we are testing a PostgreSQL stored procedure, we
        # should pass it UTF-8 encoded strings to match our database encoding.
        self.failUnlessEqual(
                self.person_sort_key(
                    u"Bj\N{LATIN SMALL LETTER O WITH DIAERESIS}rn".encode(
                        "UTF-8"), "bjorn"),
                u"bj\xf6rn, bjorn"
                )

        # Case conversion is handled correctly using Unicode
        self.failUnlessEqual(
                self.person_sort_key(
                    u"Bj\N{LATIN CAPITAL LETTER O WITH DIAERESIS}rn".encode(
                        "UTF-8"), "bjorn"),
                u"bj\xf6rn, bjorn" # Lower case o with diaeresis
                )


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

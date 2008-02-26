# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from canonical.testing import LaunchpadLayer

class KarmaSampleDataTestCase(unittest.TestCase):
    layer = LaunchpadLayer

    def test_karma_sample_data(self):
        # Test to ensure that all sample karma events are far enough in
        # the past that they won't decay over time.
        con = self.layer.connect()
        cur = con.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM Karma
            WHERE datecreated > '2002-01-01 00:00'::timestamp
            """)
        dud_rows = cur.fetchone()[0]
        self.failUnlessEqual(
                dud_rows, 0, 'Karma time bombs added to sampledata')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

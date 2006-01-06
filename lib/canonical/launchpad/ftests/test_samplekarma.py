# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest
from harness import LaunchpadTestCase

class KarmaSampleDataTestCase(LaunchpadTestCase):
    def test_karma_sample_data(self):
        # Test to ensure that all sample karma events are far enough in
        # the future that they will not cause tests to fail as time goes
        # by (as karma becomes worth less the further in the past it is)
        con = self.connect()
        cur = con.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM Karma
            WHERE datecreated < '2025-01-01 00:00'::timestamp
            """)
        dud_rows = cur.fetchone()[0]
        self.failUnlessEqual(
                dud_rows, 0, 'Karma time bombs added to sampledata'
                )


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(KarmaSampleDataTestCase))
    return suite


if __name__ == '__main__':
    unittest.main()

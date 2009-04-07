# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Shipping constraint tests."""

__metaclass__ = type

import unittest
import psycopg2

from canonical.database.sqlbase import quote
from canonical.launchpad.interfaces.shipit import ShippingRequestStatus
from canonical.testing import LaunchpadLayer


class ShipitConstraintsTestCase(unittest.TestCase):
    layer = LaunchpadLayer

    def shipped(self, cur, id):
        cur.execute("""
            SELECT shipped IS NOT NULL FROM ShippingRequest WHERE id=%(id)s
            """, vars()
            )
        return cur.fetchone()[0]

    def insert(self, cur, is_admin_request='false'):
        cur.execute("""
            INSERT INTO ShippingRequest (
                recipient, recipientdisplayname, addressline1, city,
                country, status, is_admin_request)
            VALUES (
                (SELECT account FROM Person WHERE name='stub'),
                'whatever', 'whatever', 'whatever', 66, 1,
                %(is_admin_request)s
                )
            """, vars())
        cur.execute("SELECT currval('shippingrequest_id_seq')")
        return cur.fetchone()[0]

    def testDupeAdminRequests(self):
        # Duplicate shipments are ignored if the recipient is shipit-admins
        cur = self.layer.connect().cursor()
        for i in range(0, 3):
            self.insert(cur, is_admin_request='true')

    def testDupes(self):
        # Only one uncancelled, possibly approved unshipped order
        # per user.
        con = self.layer.connect()
        cur = con.cursor()

        # Clear out any existing requests for user stub
        cur.execute("""
            DELETE FROM RequestedCDs USING ShippingRequest, Person
            WHERE recipient = Person.account and Person.name = 'stub'
                AND RequestedCDs.request = ShippingRequest.id
            """)
        cur.execute("""
            DELETE FROM ShippingRequest USING Person
            WHERE recipient = Person.account and Person.name = 'stub'
            """)

        # Create some denied orders
        denied = quote(ShippingRequestStatus.DENIED)
        for i in range(0, 3):
            disallowed_id = self.insert(cur)
            cur.execute("""
                UPDATE ShippingRequest SET status=%(denied)s
                WHERE id = %(disallowed_id)s
                """, vars())

        # Create some cancelled orders
        cancelled = quote(ShippingRequestStatus.CANCELLED)
        for i in range(0, 3):
            cancelled_id = self.insert(cur)
            cur.execute("""
                UPDATE ShippingRequest SET status=%(cancelled)s
                WHERE id = %(cancelled_id)s
                """, vars())

        # Try to create two orders, neither approved. The second should fail.
        cur.execute("SAVEPOINT attempt1")
        self.insert(cur)
        self.failUnlessRaises(psycopg2.Error, self.insert, cur)
        cur.execute("ROLLBACK TO SAVEPOINT attempt1")

        # Try to create two orders, the first explicitly approved. The
        # second should still fail.
        cur.execute("SAVEPOINT attempt2")
        req1_id = self.insert(cur)
        approved = quote(ShippingRequestStatus.APPROVED)
        cur.execute("""
            UPDATE ShippingRequest SET status=%(approved)s, whoapproved=11
            WHERE id = %(req1_id)s
            """, vars())
        self.failUnlessRaises(psycopg2.Error, self.insert, cur)
        cur.execute("ROLLBACK TO SAVEPOINT attempt2")


def test_suite():
    """Create the test suite.."""
    return unittest.TestLoader().loadTestsFromName(__name__)


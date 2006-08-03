# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest
import psycopg

from canonical.lp.dbschema import ShippingRequestStatus
from canonical.launchpad.ftests.harness import LaunchpadFunctionalTestCase

class ShipitConstraintsTestCase(LaunchpadFunctionalTestCase):
    def shipped(self, cur, id):
        cur.execute("""
            SELECT shipped IS NOT NULL FROM ShippingRequest WHERE id=%(id)s
            """, vars()
            )
        return cur.fetchone()[0]

    def insert(self, cur, owner='stub'):
        cur.execute("""
            INSERT INTO ShippingRequest (
                recipient, recipientdisplayname, addressline1, city,
                country, status)
            VALUES (
                (SELECT id FROM Person WHERE name=%(owner)s),
                'whatever', 'whatever', 'whatever', 66, 1
                )
            """, vars())
        cur.execute("SELECT currval('shippingrequest_id_seq')")
        return cur.fetchone()[0]

    def testDupeAdminRequests(self):
        # Duplicate shipments are ignored if the recipient is shipit-admins
        cur = self.connect().cursor()
        for i in range(0, 3):
            self.insert(cur, 'shipit-admins')

    def testDupes(self):
        # Only one uncancelled, possibly approved unshipped order
        # per user.
        con = self.connect()
        cur = con.cursor()

        # Clear out any existing requests for user stub
        cur.execute("""
            DELETE FROM RequestedCDs USING ShippingRequest, Person
            WHERE recipient = Person.id and Person.name = 'stub'
                AND RequestedCDs.request = ShippingRequest.id
            """)
        cur.execute("""
            DELETE FROM ShippingRequest USING Person
            WHERE recipient = Person.id and Person.name = 'stub'
            """)

        # Create some denied orders
        denied = ShippingRequestStatus.DENIED
        for i in range(0, 3):
            disallowed_id = self.insert(cur)
            cur.execute("""
                UPDATE ShippingRequest SET status=%(denied)s
                WHERE id = %(disallowed_id)s
                """, vars())

        # Create some cancelled orders
        cancelled = ShippingRequestStatus.CANCELLED
        for i in range(0, 3):
            cancelled_id = self.insert(cur)
            cur.execute("""
                UPDATE ShippingRequest SET status=%(cancelled)s
                WHERE id = %(cancelled_id)s
                """, vars())

        # Try to create two orders, neither approved. The second should fail.
        cur.execute("SAVEPOINT attempt1")
        self.insert(cur)
        self.failUnlessRaises(psycopg.Error, self.insert, cur)
        cur.execute("ROLLBACK TO SAVEPOINT attempt1")

        # Try to create two orders, the first explicitly approved. The
        # second should still fail.
        cur.execute("SAVEPOINT attempt2")
        req1_id = self.insert(cur)
        approved = ShippingRequestStatus.APPROVED
        cur.execute("""
            UPDATE ShippingRequest SET status=%(approved)s, whoapproved=1
            WHERE id = %(req1_id)s
            """, vars())
        self.failUnlessRaises(psycopg.Error, self.insert, cur)
        cur.execute("ROLLBACK TO SAVEPOINT attempt2")


def test_suite():
    return unittest.makeSuite(ShipitConstraintsTestCase)


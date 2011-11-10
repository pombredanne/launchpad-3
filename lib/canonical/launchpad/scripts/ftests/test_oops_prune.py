# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the oops-prune.py cronscript and methods in the
   canonical.launchpad.scripts.oops module.
"""

__metaclass__ = type

import unittest

import transaction

from canonical.database.sqlbase import cursor
from canonical.launchpad.scripts.oops import referenced_oops
from canonical.testing.layers import LaunchpadZopelessLayer


class TestOopsPrune(unittest.TestCase):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        # Create a reference to one of the old OOPS reports in the DB
        self.referenced_oops_code = 'OOPS-2A666'
        cur = cursor()
        cur.execute("""
            INSERT INTO MessageChunk(message, sequence, content)
            VALUES (1, 99, '%s')
            """ % self.referenced_oops_code)
        # Need to commit or the changes are not visible on the slave.
        transaction.commit()

    def test_referenced_oops(self):
        self.failUnlessEqual(
                set([self.referenced_oops_code]),
                referenced_oops()
                )

        # We also check in other places besides MessageChunk for oops ids
        cur = cursor()
        cur.execute("UPDATE Message SET subject='OOPS-MessageSubject666'")
        cur.execute("""
            UPDATE Bug SET
                title='OOPS-1BugTitle666',
                description='OOPS-1BugDescription666'
            """)
        cur.execute("""
            UPDATE Question SET
                title='OOPS - 1TicketTitle666 bar',
                description='http://foo.com OOPS-1TicketDescription666',
                whiteboard='OOPS-1TicketWhiteboard666'
                WHERE id=1
            """)
        # Add a question entry with a NULL whiteboard to ensure the SQL query
        # copes.
        cur.execute("""
            UPDATE Question SET
                title='OOPS - 1TicketTitle666 bar',
                description='http://foo.com OOPS-1TicketDescription666',
                whiteboard=NULL
                WHERE id=2
            """)

        # Need to commit or the changes are not visible on the slave.
        transaction.commit()

        self.failUnlessEqual(
                set([
                    self.referenced_oops_code,
                    'OOPS-MESSAGESUBJECT666',
                    'OOPS-1BUGTITLE666',
                    'OOPS-1BUGDESCRIPTION666',
                    'OOPS-1TICKETTITLE666',
                    'OOPS-1TICKETDESCRIPTION666',
                    'OOPS-1TICKETWHITEBOARD666',
                    ]),
                referenced_oops()
                )

    def test_referenced_oops_in_urls(self):
        # Sometimes OOPS ids appears as part of an URL. We don't want the
        # POSIX regexp matching on those OOPS ids since the FormattersAPI
        # doesn't match them.
        cur = cursor()
        cur.execute("""
        UPDATE Bug SET
            title='Some title',
            description=
                'https://lp-oops.canonical.com/oops.py/?oopsid=OOPS-1Foo666'
        """)
        self.failUnlessEqual(
                set([self.referenced_oops_code]),
                referenced_oops())

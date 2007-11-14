#! /usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Populate POMsgSet's language column."""

__metaclass__ = type
__all__ = []

import _pythonpath

from zope.interface import implements

from canonical.database.sqlbase import cursor
from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.scripts.base import LaunchpadScript
from canonical.launchpad.utilities.looptuner import LoopTuner


class FillLanguageColumn:
    """Initialize chunks of POMsgSet.language to matching POFile.language."""
    implements(ITunableLoop)

    def __init__(self, transaction_manager):
        """See `ITunableLoop`."""
        self.transaction_manager = transaction_manager
        cur = cursor()
        cur.execute("SELECT min(id), max(id) FROM POMsgSet")
        self.lowest_id, self.highest_id = cur.fetchone()

        if self.lowest_id is None:
            # Table is empty.  We weren't expecting this!
            raise AssertionError("POMsgSet table is empty")

    def isDone(self):
        """See `ITunableLoop`."""
        return self.lowest_id is None or self.lowest_id > self.highest_id

    def __call__(self, batch_size):
        """See `ITunableLoop`."""
        batch_size = int(batch_size)
        cur = cursor()

        # Find id of first row of next batch.  This takes a bit of time to
        # compute, but it'll give us more regular timings than just adding
        # batch_size to self.lowest_id.  If we did that, "holes" in the id
        # sequence could drive up batch sizes to irresponsible heights.
        # Hitting a more densely populated id range after that could lead to
        # traumatic delays.
        cur.execute("""
            SELECT max(id)
            FROM (
                SELECT id
                FROM POMsgSet
                WHERE id >= %d
                ORDER BY id
                LIMIT %d)
                AS id
            """ % (self.lowest_id, batch_size))
        next = cur.fetchone()[0]
        if next is not None:
            next += 1
            cur.execute("""
                UPDATE POMsgSet
                SET language = POFile.language
                FROM POFile
                WHERE
                    POFile.id = POMsgSet.pofile AND
                    POMsgSet.id >= %d AND
                    POMsgSet.id < %d AND
                    POMsgSet.language IS NULL
                    """
                % (self.lowest_id, next))
            self.transaction_manager.commit()
            self.transaction_manager.begin()

        self.lowest_id = next


def check_for_mismatches():
    """Verify that `POMsgSet.language` fields match corresponding `POFiles`'.

    Raises AssertionError if a mismatch is found.

    Null values are quietly ignored; this function can be run before or after
    the `language` column is populated.
    """
    cur = cursor()
    cur.execute("""
        SELECT count(*)
        FROM POMsgSet
        JOIN POFile ON POMsgSet.pofile = POFile.id
        WHERE POMsgSet.language <> POFile.language
        """)
    mismatches = cur.fetchone()[0]
    if mismatches != 0:
        raise AssertionError("%d mismatches between POMsgSet languages "
            "and POFile languages" % mismatches)


def check_for_nulls():
    """Verify that no nulls are left in the `POMsgSet.language` column.

    Raises AssertionError if nulls are found.
    """
    cur = cursor()
    cur.execute("SELECT count(*) FROM POMsgSet WHERE language IS NULL")
    nulls = cur.fetchone()[0]
    if nulls != 0:
        raise AssertionError(
            "%d nulls found among POMsgSet languages" % nulls)


class InitializePOMsgSetLanguage(LaunchpadScript):
    """A script, for one-time use only, to initialize POMsgSet.language."""

    def main(self):
        self.logger.info("Checking for existing mismatches...")
        check_for_mismatches()

        self.logger.info("Populating POMsgSet.language column...")
        filler = FillLanguageColumn(self.txn)
        LoopTuner(filler, 1, 10, 3000).run()

        self.logger.info("Checking for remaining nulls...")
        check_for_nulls()

        self.logger.info("Checking for incorrectly filled language fields...")
        check_for_mismatches()

        self.logger.info("Committing...")
        self.txn.commit()
        self.logger.info("Done.")

if __name__ == '__main__':
    script = InitializePOMsgSetLanguage('initialize-pomsgset-language')
    script.lock_and_run()


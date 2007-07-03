#! /usr/bin/python2.4

"""Populate POMsgSet's language column."""

from canonical.database.sqlbase import cursor
from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.scripts.base import LaunchpadScript
from canonical.launchpad.utilities.looptuner import LoopTuner

from zope.interface import implements

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


class InitializePOMsgSetLanguage(LaunchpadScript):
    """A script, for one-time use only, to initialize POMsgSet.language."""

    def main(self):
        filler = FillLanguageColumn(self.txn)
        LoopTuner(filler, 4).run()
        self.logger.info("Done.")

if __name__ == '__main__':
    script = InitializePOMsgSetLanguage('initialize-pomsgset-language')
    script.lock_and_run()


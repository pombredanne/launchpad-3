# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Code for the BugWatch scheduler."""

__metaclass__ = type
__all__ = [
    'BugWatchScheduler',
    ]

import transaction

from canonical.database.sqlbase import sqlvalues
from canonical.launchpad.utilities.looptuner import TunableLoop
from canonical.launchpad.interfaces import IMasterStore

from lp.bugs.model.bugwatch import BugWatch


class BugWatchScheduler(TunableLoop):
    """An `ITunableLoop` for scheduling BugWatches."""

    def __call__(self, chunk_size):
        """Run the loop."""
        query = """
        UPDATE BugWatch
            SET next_check =
                COALESCE(
                    lastchecked + interval '1 day',
                    now() AT TIME ZONE 'UTC') +
                (interval '1 day' * (1.2 * recent_failure_count))
            FROM (
                SELECT bug_watch.id,
                    (SELECT COUNT(*)
                        FROM (SELECT 1
                            FROM bugwatchactivity
                           WHERE bugwatchactivity.bug_watch = bug_watch.id
                             AND bugwatchactivity.result IS NOT NULL
                           ORDER BY bugwatchactivity.id
                           LIMIT 5) AS recent_failures
                    ) AS recent_failure_count
                FROM BugWatch AS bug_watch
                WHERE bug_watch.next_check IS NULL
                LIMIT %s
            ) AS counts
        WHERE BugWatch.id = counts.id;
        """ % sqlvalues(chunk_size)

        self.store = IMasterStore(BugWatch)
        transaction.begin()
        self.store.execute(query)
        transaction.commit()

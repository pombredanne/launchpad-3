# Copyright 2008 Canonical Ltd.  All rights reserved.

"""A utility module for the update-bugtasktargetnamecaches.py cronscript."""

__metaclass__ = type
__all__ = ['BugTaskTargetNameCachesTunableLoop']

from zope.component import getUtility
from zope.interface import implements

from canonical.database.sqlbase import quote
from canonical.launchpad.database import BugTask
from canonical.launchpad.interfaces.looptuner import ITunableLoop


class BugTaskTargetNameCachesTunableLoop(object):
    """An `ITunableLoop` for updating BugTask targetname caches."""

    implements(ITunableLoop)

    total_updated = 0

    def __init__(self, transaction, logger, start_at_id=0):
        self.transaction = transaction
        self.logger = logger
        self.start_at_id = start_at_id

    def isDone(self):
        """See `ITunableLoop`."""
        # When the main loop has no more BugTasks to process it sets
        # start_at_id to None. Until then, it always has a numerical
        # value.
        return self.start_at_id is None

    def __call__(self, chunk_size):
        """Retrieve a batch of BugTasks and update their targetname caches.

        See `ITunableLoop`.
        """
        offset = self.start_at_id
        bugtasks = BugTask.select(orderBy="id")[offset:offset + chunk_size]

        self.logger.info("Updating %i BugTasks (starting id: %i)." %
            (chunk_size, self.start_at_id))
        self.start_at_id = None
        self.transaction.begin()
        for bugtask in bugtasks:
            # We set the starting point of the next batch to the BugTask
            # after the one we're looking at now. If there aren't any
            # bugtasks this loop will run for 0 iterations and start_id
            # will remain set to None.
            self.start_at_id = bugtask.id + 1
            bugtask.updateTargetNameCache()
            self.total_updated += 1

        self.transaction.commit()



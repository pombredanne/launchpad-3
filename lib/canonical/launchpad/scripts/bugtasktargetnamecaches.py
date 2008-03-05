# Copyright 2008 Canonical Ltd.  All rights reserved.

"""A utility module for the update-bugtasktargetnamecaches.py cronscript."""

__metaclass__ = type
__all__ = ['BugTaskTargetNameCacheUpdater']

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import IBugTaskSet
from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.utilities.looptuner import LoopTuner


class BugTaskTargetNameCachesTunableLoop(object):
    """An `ITunableLoop` for updating BugTask targetname caches."""

    implements(ITunableLoop)

    total_updated = 0

    def __init__(self, transaction, logger, offset=0):
        self.transaction = transaction
        self.logger = logger
        self.offset = offset
        self.total_updated = 0

        self.transaction.begin()
        self.bugtasks = list(getUtility(IBugTaskSet).dangerousGetAllTasks())
        self.transaction.commit()

    def isDone(self):
        """See `ITunableLoop`."""
        # When the main loop has no more BugTasks to process it sets
        # offset to None. Until then, it always has a numerical
        # value.
        return self.total_updated == len(self.bugtasks)

    def __call__(self, chunk_size):
        """Retrieve a batch of BugTasks and update their targetname caches.

        See `ITunableLoop`.
        """
        # We cast chunk_size to an integer to ensure that we're not
        # trying to slice using floats or anything similarly foolish.
        chunk_size = int(chunk_size)
        bugtasks = self.bugtasks[self.offset:self.offset + chunk_size]

        starting_id = bugtasks[0].id
        self.logger.info("Updating %i BugTasks (starting id: %i)." %
            (len(bugtasks), starting_id))

        self.transaction.begin()
        for bugtask in bugtasks:
            # We set the starting point of the next batch to the BugTask
            # id after the one we're looking at now. If there aren't any
            # bugtasks this loop will run for 0 iterations and start_id
            # will remain set to None.
            self.offset += 1
            bugtask.updateTargetNameCache()
            self.total_updated += 1

        self.transaction.commit()


class BugTaskTargetNameCacheUpdater:
    """A runnable class which updates the bugtask target name caches."""

    def __init__(self, transaction, logger):
        self.transaction = transaction
        self.logger = logger

    def run(self):
        """Update the bugtask target name caches."""
        self.logger.info("Updating targetname cache of bugtasks.")
        loop = BugTaskTargetNameCachesTunableLoop(
            self.transaction, self.logger)

        loop_tuner = LoopTuner(loop, 2)
        loop_tuner.run()

        self.logger.info("Updated %i bugtask targetname caches." %
            loop.total_updated)
        self.logger.info("Finished updating targetname cache of bugtasks.")


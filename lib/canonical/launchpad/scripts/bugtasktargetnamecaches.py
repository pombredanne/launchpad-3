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
        self.bugtask_set = getUtility(IBugTaskSet)

    def isDone(self):
        """See `ITunableLoop`."""
        # When the main loop has no more BugTasks to process it sets
        # offset to None. Until then, it always has a numerical
        # value.
        return self.offset is None

    def __call__(self, chunk_size):
        """Retrieve a batch of BugTasks and update their targetname caches.

        See `ITunableLoop`.
        """
        offset = self.offset
        bugtasks = self.bugtask_set.dangerousGetAllTasks()[
            offset:offset + chunk_size]

        self.logger.info("Updating up to %i BugTasks (starting id: %i)." %
            (chunk_size, offset))

        self.offset = None
        self.transaction.begin()
        for bugtask in bugtasks:
            # We set the starting point of the next batch to the BugTask
            # id after the one we're looking at now. If there aren't any
            # bugtasks this loop will run for 0 iterations and start_id
            # will remain set to None.
            offset += 1
            self.offset = offset
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

        loop_tuner = LoopTuner(loop, 5)
        loop_tuner.run()

        self.logger.info("Updated %i bugtask targetname caches." %
            loop.total_updated)
        self.logger.info("Finished updating targetname cache of bugtasks.")


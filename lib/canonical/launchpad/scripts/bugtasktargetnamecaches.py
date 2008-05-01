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
        # XXX 2008-03-05 gmb:
        #     We cast chunk_size to an integer to ensure that we're not
        #     trying to slice using floats or anything similarly
        #     foolish. We shouldn't have to do this, but bug #198767
        #     means that we do.
        chunk_size = int(chunk_size)

        start = self.offset
        end = self.offset + chunk_size

        self.transaction.begin()
        # XXX: kiko 2006-03-23:
        # We use a special API here, which is kinda klunky, but which
        # allows us to return all bug tasks (even private ones); this should
        # eventually be changed to a more elaborate permissions scheme,
        # pending the infrastructure to do so. See bug #198778.
        bugtasks = list(
            getUtility(IBugTaskSet).dangerousGetAllTasks()[start:end])

        self.offset = None
        if bugtasks:
            starting_id = bugtasks[0].id
            self.logger.info("Updating %i BugTasks (starting id: %i)." %
                (len(bugtasks), starting_id))

        for bugtask in bugtasks:
            # We set the starting point of the next batch to the BugTask
            # id after the one we're looking at now. If there aren't any
            # bugtasks this loop will run for 0 iterations and start_id
            # will remain set to None.
            start += 1
            self.offset = start
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

        # We use the LoopTuner class to try and get an ideal number of
        # bugtasks updated for each iteration of the loop (see the
        # LoopTuner documentation for more details).
        loop_tuner = LoopTuner(loop, 2)
        loop_tuner.run()

        self.logger.info("Updated %i bugtask targetname caches." %
            loop.total_updated)
        self.logger.info("Finished updating targetname cache of bugtasks.")


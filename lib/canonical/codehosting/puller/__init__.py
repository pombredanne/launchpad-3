# Copyright 2006 Canonical Ltd.  All rights reserved.

import datetime

import pytz

from twisted.internet import defer

from canonical.codehosting.puller.scheduler import LockError


UTC = pytz.timezone('UTC')


def mirror(logger, manager):
    """Mirror all current branches that need to be mirrored."""
    try:
        manager.lock()
    except LockError, exception:
        logger.info('Could not acquire lock: %s', exception)
        return defer.succeed(0)

    date_started = datetime.datetime.now(UTC)

    def recordSuccess(ignored):
        date_completed = datetime.datetime.now(UTC)
        manager.recordActivity(date_started, date_completed)

    def unlock(ignored):
        manager.unlock()

    deferred = manager.run(logger)
    deferred.addCallback(recordSuccess)
    deferred.addBoth(unlock)
    return deferred


# Copyright 2009-2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Soyuz buildd slave manager logic."""

__metaclass__ = type

__all__ = [
    'BuilddManager',
    'BUILDD_MANAGER_LOG_NAME',
    ]

import datetime
import functools
import logging

from storm.expr import LeftJoin
import transaction
from twisted.application import service
from twisted.internet import (
    defer,
    reactor,
    )
from twisted.internet.task import LoopingCall
from twisted.python import log
from zope.component import getUtility

from lp.buildmaster.enums import (
    BuilderCleanStatus,
    BuildQueueStatus,
    BuildStatus,
    )
from lp.buildmaster.interactor import (
    BuilderInteractor,
    extract_vitals_from_db,
    )
from lp.buildmaster.interfaces.builder import (
    BuildDaemonError,
    BuildDaemonIsolationError,
    BuildSlaveFailure,
    CannotBuild,
    CannotFetchFile,
    CannotResumeHost,
    IBuilderSet,
    )
from lp.buildmaster.model.builder import Builder
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.services.database.interfaces import IStore
from lp.services.propertycache import get_property_cache


BUILDD_MANAGER_LOG_NAME = "slave-scanner"


class BuilderFactory:
    """A dumb builder factory that just talks to the DB."""

    def update(self):
        """Update the factory's view of the world.

        For the basic BuilderFactory this is a no-op, but others might do
        something.
        """
        return

    def prescanUpdate(self):
        """Update the factory's view of the world before each scan.

        For the basic BuilderFactory this means ending the transaction
        to ensure that data retrieved is up to date.
        """
        transaction.abort()

    @property
    def date_updated(self):
        return datetime.datetime.utcnow()

    def __getitem__(self, name):
        """Get the named `Builder` Storm object."""
        return getUtility(IBuilderSet).getByName(name)

    def getVitals(self, name):
        """Get the named `BuilderVitals` object."""
        return extract_vitals_from_db(self[name])

    def iterVitals(self):
        """Iterate over all `BuilderVitals` objects."""
        return (
            extract_vitals_from_db(b)
            for b in getUtility(IBuilderSet).__iter__())


class PrefetchedBuilderFactory:
    """A smart builder factory that does efficient bulk queries.

    `getVitals` and `iterVitals` don't touch the DB directly. They work
    from cached data updated by `update`.
    """

    date_updated = None

    def update(self):
        """See `BuilderFactory`."""
        transaction.abort()
        builders_and_bqs = IStore(Builder).using(
            Builder, LeftJoin(BuildQueue, BuildQueue.builderID == Builder.id)
            ).find((Builder, BuildQueue))
        self.vitals_map = dict(
            (b.name, extract_vitals_from_db(b, bq))
            for b, bq in builders_and_bqs)
        transaction.abort()
        self.date_updated = datetime.datetime.utcnow()

    def prescanUpdate(self):
        """See `BuilderFactory`.

        This is a no-op, as the data was already brought sufficiently up
        to date by update().
        """
        return

    def __getitem__(self, name):
        """See `BuilderFactory`."""
        return getUtility(IBuilderSet).getByName(name)

    def getVitals(self, name):
        """See `BuilderFactory`."""
        return self.vitals_map[name]

    def iterVitals(self):
        """See `BuilderFactory`."""
        return (b for n, b in sorted(self.vitals_map.iteritems()))


def judge_failure(builder_count, job_count, exc, retry=True):
    """Judge how to recover from a scan failure.

    Assesses the failure counts of a builder and its current job, and
    determines the best course of action for recovery.

    :param: builder_count: Count of consecutive failures of the builder.
    :param: job_count: Count of consecutive failures of the job.
    :param: exc: Exception that caused the failure, if any.
    :param: retry: Whether to retry a few times without taking action.
    :return: A tuple of (builder action, job action). True means reset,
        False means fail, None means take no action.
    """
    if isinstance(exc, BuildDaemonIsolationError):
        # We have a potential security issue. Insta-kill both regardless
        # of any failure counts.
        return (False, False)

    if builder_count == job_count:
        # We can't tell which is to blame. Retry a few times, and then
        # reset the job so it can be retried elsewhere. If the job is at
        # fault, it'll error on the next builder and fail out. If the
        # builder is at fault, the job will work fine next time, and the
        # builder will error on the next job and fail out.
        if not retry or builder_count >= Builder.JOB_RESET_THRESHOLD:
            return (None, True)
    elif builder_count > job_count:
        # The builder has failed more than the job, so the builder is at
        # fault. We reset the job, and attempt to recover the builder.
        # We retry a few times, then reset the builder. Then try a few
        # more times, then reset it again. Then try yet again, after
        # which we fail.
        # XXX: Rescanning a virtual builder without resetting is stupid,
        # as it will be reset anyway due to being dirty and idle.
        if (builder_count >=
                Builder.RESET_THRESHOLD * Builder.RESET_FAILURE_THRESHOLD):
            return (False, True)
        elif builder_count % Builder.RESET_THRESHOLD == 0:
            return (True, True)
        return (None, True)
    else:
        # The job has failed more than the builder. Fail it.
        return (None, False)

    # Just retry.
    return (None, None)


@defer.inlineCallbacks
def assessFailureCounts(logger, vitals, builder, slave, interactor, retry,
                        exception):
    """View builder/job failure_count and work out which needs to die.

    :return: A Deferred that fires either immediately or after a virtual
        slave has been reset.
    """
    del get_property_cache(builder).currentjob
    job = builder.currentjob

    # If a job is being cancelled we won't bother retrying a failure.
    # Just mark it as cancelled and clear the builder for normal cleanup.
    cancelling = job is not None and job.status == BuildQueueStatus.CANCELLING
    builder_action, job_action = judge_failure(
        builder.failure_count, job.specific_build.failure_count if job else 0,
        exception, retry=retry and not cancelling)

    if job is not None and job_action is not None:
        if job_action == False:
            # We've decided the job is bad, so unblame the builder.
            builder.resetFailureCount()

        if cancelling:
            # We've previously been asked to cancel the job, so just set
            # it to cancelled rather than retrying or failing.
            job.markAsCancelled()
        elif job_action == False:
            # Fail and dequeue the job.
            job.specific_build.updateStatus(BuildStatus.FAILEDTOBUILD)
            job.destroySelf()
        elif job_action == True:
            # Reset the job so it will be retried elsewhere.
            job.reset()

    if builder_action == False:
        # We've already tried resetting it enough times, so we have
        # little choice but to give up.
        builder.failBuilder(str(exception))
    elif builder_action == True:
        # The builder is dead, but in the virtual case it might be worth
        # resetting it.
        yield interactor.resetOrFail(
            vitals, slave, builder, logger, exception)
    del get_property_cache(builder).currentjob


class SlaveScanner:
    """A manager for a single builder."""

    # The interval between each poll cycle, in seconds.  We'd ideally
    # like this to be lower but 15 seems a reasonable compromise between
    # responsivity and load on the database server, since in each cycle
    # we can run quite a few queries.
    #
    # NB. This used to be as low as 5 but as more builders are added to
    # the farm this rapidly increases the query count, PG load and this
    # process's load.  It's backed off until we come up with a better
    # algorithm for polling.
    SCAN_INTERVAL = 15

    # The time before deciding that a cancelling builder has failed, in
    # seconds.  This should normally be a multiple of SCAN_INTERVAL, and
    # greater than abort_timeout in launchpad-buildd's slave BuildManager.
    CANCEL_TIMEOUT = 180

    def __init__(self, builder_name, builder_factory, logger, clock=None,
                 interactor_factory=BuilderInteractor,
                 slave_factory=BuilderInteractor.makeSlaveFromVitals,
                 behaviour_factory=BuilderInteractor.getBuildBehaviour):
        self.builder_name = builder_name
        self.builder_factory = builder_factory
        self.logger = logger
        self.interactor_factory = interactor_factory
        self.slave_factory = slave_factory
        self.behaviour_factory = behaviour_factory
        # Use the clock if provided, so that tests can advance it.  Use the
        # reactor by default.
        if clock is None:
            clock = reactor
        self._clock = clock
        self.date_cancel = None
        self.date_scanned = None

        # We cache the build cookie, keyed on the BuildQueue, to avoid
        # hitting the DB on every scan.
        self._cached_build_cookie = None
        self._cached_build_queue = None

    def startCycle(self):
        """Scan the builder and dispatch to it or deal with failures."""
        self.loop = LoopingCall(self.singleCycle)
        self.loop.clock = self._clock
        self.stopping_deferred = self.loop.start(self.SCAN_INTERVAL)
        return self.stopping_deferred

    def stopCycle(self):
        """Terminate the LoopingCall."""
        self.loop.stop()

    def singleCycle(self):
        # Inhibit scanning if the BuilderFactory hasn't updated since
        # the last run. This doesn't matter for the base BuilderFactory,
        # as it's always up to date, but PrefetchedBuilderFactory caches
        # heavily, and we don't want to eg. forget that we dispatched a
        # build in the previous cycle.
        if (self.date_scanned is not None
            and self.date_scanned > self.builder_factory.date_updated):
            self.logger.debug(
                "Skipping builder %s (cache out of date)" % self.builder_name)
            return defer.succeed(None)

        self.logger.debug("Scanning builder %s" % self.builder_name)
        # Errors should normally be able to be retried a few times. Bits
        # of scan() which don't want retries will call _scanFailed
        # directly.
        d = self.scan()
        d.addErrback(functools.partial(self._scanFailed, True))
        d.addBoth(self._updateDateScanned)
        return d

    def _updateDateScanned(self, ignored):
        self.date_scanned = datetime.datetime.utcnow()

    @defer.inlineCallbacks
    def _scanFailed(self, retry, failure):
        """Deal with failures encountered during the scan cycle.

        1. Print the error in the log
        2. Increment and assess failure counts on the builder and job.
           If asked to retry, a single failure may not be considered fatal.

        :return: A Deferred that fires either immediately or after a virtual
            slave has been reset.
        """
        # Make sure that pending database updates are removed as it
        # could leave the database in an inconsistent state (e.g. The
        # job says it's running but the buildqueue has no builder set).
        transaction.abort()

        # If we don't recognise the exception include a stack trace with
        # the error.
        error_message = failure.getErrorMessage()
        if failure.check(
            BuildSlaveFailure, CannotBuild, CannotResumeHost,
            BuildDaemonError, CannotFetchFile):
            self.logger.info("Scanning %s failed with: %s" % (
                self.builder_name, error_message))
        else:
            self.logger.info("Scanning %s failed with: %s\n%s" % (
                self.builder_name, failure.getErrorMessage(),
                failure.getTraceback()))

        # Decide if we need to terminate the job or reset/fail the builder.
        vitals = self.builder_factory.getVitals(self.builder_name)
        builder = self.builder_factory[self.builder_name]
        try:
            builder.handleFailure(self.logger)
            yield assessFailureCounts(
                self.logger, vitals, builder, self.slave_factory(vitals),
                self.interactor_factory(), retry, failure.value)
            transaction.commit()
        except Exception:
            # Catastrophic code failure! Not much we can do.
            self.logger.error(
                "Miserable failure when trying to handle failure:\n",
                exc_info=True)
            transaction.abort()

    @defer.inlineCallbacks
    def checkCancellation(self, vitals, slave):
        """See if there is a pending cancellation request.

        If the current build is in status CANCELLING then terminate it
        immediately.

        :return: A deferred which fires when this cancellation cycle is done.
        """
        if vitals.build_queue.status != BuildQueueStatus.CANCELLING:
            self.date_cancel = None

        if self.date_cancel is None:
            self.logger.info(
                "Cancelling BuildQueue %d (%s) on %s",
                vitals.build_queue.id, self.getExpectedCookie(vitals),
                vitals.name)
            yield slave.abort()
            self.date_cancel = self._clock.seconds() + self.CANCEL_TIMEOUT
        else:
            # The BuildFarmJob will normally set the build's status to
            # something other than CANCELLING once the builder responds to
            # the cancel request.  This timeout is in case it doesn't.
            if self._clock.seconds() < self.date_cancel:
                self.logger.info(
                    "Waiting for BuildQueue %d (%s) on %s to cancel",
                    vitals.build_queue.id, self.getExpectedCookie(vitals),
                    vitals.name)
            else:
                raise BuildSlaveFailure(
                    "Timeout waiting for BuildQueue %d (%s) on %s to "
                    "cancel" % (
                    vitals.build_queue.id, self.getExpectedCookie(vitals),
                    vitals.name))

    def getExpectedCookie(self, vitals):
        """Return the build cookie expected to be held by the slave.

        Calculating this requires hitting the DB, so it's cached based
        on the current BuildQueue.
        """
        if vitals.build_queue != self._cached_build_queue:
            if vitals.build_queue is not None:
                behaviour = self.behaviour_factory(
                    vitals.build_queue, self.builder_factory[vitals.name],
                    None)
                self._cached_build_cookie = behaviour.getBuildCookie()
            else:
                self._cached_build_cookie = None
            self._cached_build_queue = vitals.build_queue
        return self._cached_build_cookie

    def updateVersion(self, vitals, slave_status):
        """Update the DB's record of the slave version if necessary."""
        version = slave_status.get("builder_version")
        if version != vitals.version:
            self.builder_factory[self.builder_name].version = version
            transaction.commit()

    @defer.inlineCallbacks
    def scan(self):
        """Probe the builder and update/dispatch/collect as appropriate.

        :return: A Deferred that fires when the scan is complete.
        """
        self.builder_factory.prescanUpdate()
        vitals = self.builder_factory.getVitals(self.builder_name)
        interactor = self.interactor_factory()
        slave = self.slave_factory(vitals)

        if vitals.build_queue is not None:
            if vitals.clean_status != BuilderCleanStatus.DIRTY:
                # This is probably a grave bug with security implications,
                # as a slave that has a job must be cleaned afterwards.
                raise BuildDaemonIsolationError(
                    "Non-dirty builder allegedly building.")

            lost_reason = None
            if not vitals.builderok:
                lost_reason = '%s is disabled' % vitals.name
            else:
                slave_status = yield slave.status()
                # Ensure that the slave has the job that we think it
                # should.
                slave_cookie = slave_status.get('build_id')
                expected_cookie = self.getExpectedCookie(vitals)
                if slave_cookie != expected_cookie:
                    lost_reason = (
                        '%s is lost (expected %r, got %r)' % (
                            vitals.name, expected_cookie, slave_cookie))

            if lost_reason is not None:
                # The slave is either confused or disabled, so reset and
                # requeue the job. The next scan cycle will clean up the
                # slave if appropriate.
                self.logger.warn(
                    "%s. Resetting BuildQueue %d.", lost_reason,
                    vitals.build_queue.id)
                vitals.build_queue.reset()
                transaction.commit()
                return

            yield self.checkCancellation(vitals, slave)

            # The slave and DB agree on the builder's state.  Scan the
            # slave and get the logtail, or collect the build if it's
            # ready.  Yes, "updateBuild" is a bad name.
            assert slave_status is not None
            yield interactor.updateBuild(
                vitals, slave, slave_status, self.builder_factory,
                self.behaviour_factory)
        else:
            if not vitals.builderok:
                return
            # We think the builder is idle. If it's clean, dispatch. If
            # it's dirty, clean.
            if vitals.clean_status == BuilderCleanStatus.CLEAN:
                slave_status = yield slave.status()
                if slave_status.get('builder_status') != 'BuilderStatus.IDLE':
                    raise BuildDaemonIsolationError(
                        'Allegedly clean slave not idle (%r instead)'
                        % slave_status.get('builder_status'))
                self.updateVersion(vitals, slave_status)
                if vitals.manual:
                    # If the builder is in manual mode, don't dispatch
                    # anything.
                    self.logger.debug(
                        '%s is in manual mode, not dispatching.', vitals.name)
                    return
                # Try to find and dispatch a job. If it fails, don't
                # attempt to just retry the scan; we need to reset
                # the job so the dispatch will be reattempted.
                builder = self.builder_factory[self.builder_name]
                d = interactor.findAndStartJob(vitals, builder, slave)
                d.addErrback(functools.partial(self._scanFailed, False))
                yield d
                if builder.currentjob is not None:
                    # After a successful dispatch we can reset the
                    # failure_count.
                    builder.resetFailureCount()
                    transaction.commit()
            else:
                # Ask the BuilderInteractor to clean the slave. It might
                # be immediately cleaned on return, in which case we go
                # straight back to CLEAN, or we might have to spin
                # through another few cycles.
                done = yield interactor.cleanSlave(
                    vitals, slave, self.builder_factory)
                if done:
                    builder = self.builder_factory[self.builder_name]
                    builder.setCleanStatus(BuilderCleanStatus.CLEAN)
                    self.logger.debug('%s has been cleaned.', vitals.name)
                    transaction.commit()


class NewBuildersScanner:
    """If new builders appear, create a scanner for them."""

    # How often to check for new builders, in seconds.
    SCAN_INTERVAL = 15

    def __init__(self, manager, clock=None):
        self.manager = manager
        # Use the clock if provided, it's so that tests can
        # advance it.  Use the reactor by default.
        if clock is None:
            clock = reactor
        self._clock = clock
        self.current_builders = []

    def stop(self):
        """Terminate the LoopingCall."""
        self.loop.stop()

    def scheduleScan(self):
        """Schedule a callback SCAN_INTERVAL seconds later."""
        self.loop = LoopingCall(self.scan)
        self.loop.clock = self._clock
        self.stopping_deferred = self.loop.start(self.SCAN_INTERVAL)
        return self.stopping_deferred

    def scan(self):
        """If a new builder appears, create a SlaveScanner for it."""
        try:
            self.manager.builder_factory.update()
            new_builders = self.checkForNewBuilders()
            self.manager.addScanForBuilders(new_builders)
        except Exception:
            self.manager.logger.error(
                "Failure while updating builders:\n",
                exc_info=True)
            transaction.abort()

    def checkForNewBuilders(self):
        """See if any new builders were added."""
        new_builders = set(
            vitals.name for vitals in
            self.manager.builder_factory.iterVitals())
        old_builders = set(self.current_builders)
        extra_builders = new_builders.difference(old_builders)
        self.current_builders.extend(extra_builders)
        return list(extra_builders)


class BuilddManager(service.Service):
    """Main Buildd Manager service class."""

    def __init__(self, clock=None, builder_factory=None):
        self.builder_slaves = []
        self.builder_factory = builder_factory or PrefetchedBuilderFactory()
        self.logger = self._setupLogger()
        self.new_builders_scanner = NewBuildersScanner(
            manager=self, clock=clock)

    def _setupLogger(self):
        """Set up a 'slave-scanner' logger that redirects to twisted.

        Make it less verbose to avoid messing too much with the old code.
        """
        level = logging.INFO
        logger = logging.getLogger(BUILDD_MANAGER_LOG_NAME)
        logger.propagate = False

        # Redirect the output to the twisted log module.
        channel = logging.StreamHandler(log.StdioOnnaStick())
        channel.setLevel(level)
        channel.setFormatter(logging.Formatter('%(message)s'))

        logger.addHandler(channel)
        logger.setLevel(level)
        return logger

    def startService(self):
        """Service entry point, called when the application starts."""
        # Ask the NewBuildersScanner to add and start SlaveScanners for
        # each current builder, and any added in the future.
        self.new_builders_scanner.scheduleScan()

    def stopService(self):
        """Callback for when we need to shut down."""
        # XXX: lacks unit tests
        # All the SlaveScanner objects need to be halted gracefully.
        deferreds = [slave.stopping_deferred for slave in self.builder_slaves]
        deferreds.append(self.new_builders_scanner.stopping_deferred)

        self.new_builders_scanner.stop()
        for slave in self.builder_slaves:
            slave.stopCycle()

        # The 'stopping_deferred's are called back when the loops are
        # stopped, so we can wait on them all at once here before
        # exiting.
        d = defer.DeferredList(deferreds, consumeErrors=True)
        return d

    def addScanForBuilders(self, builders):
        """Set up scanner objects for the builders specified."""
        for builder in builders:
            slave_scanner = SlaveScanner(
                builder, self.builder_factory, self.logger)
            self.builder_slaves.append(slave_scanner)
            slave_scanner.startCycle()

        # Return the slave list for the benefit of tests.
        return self.builder_slaves

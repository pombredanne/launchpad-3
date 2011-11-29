# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Soyuz buildd slave manager logic."""

__metaclass__ = type

__all__ = [
    'BuilddManager',
    'BUILDD_MANAGER_LOG_NAME',
    ]

import logging

import transaction
from twisted.application import service
from twisted.internet import (
    defer,
    reactor,
    )
from twisted.internet.task import LoopingCall
from twisted.python import log
from zope.component import getUtility

from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.builder import (
    BuildDaemonError,
    BuildSlaveFailure,
    CannotBuild,
    CannotFetchFile,
    CannotResumeHost,
    )
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    BuildBehaviorMismatch,
    )
from lp.buildmaster.model.builder import Builder
from lp.services.database.transaction_policy import DatabaseTransactionPolicy


BUILDD_MANAGER_LOG_NAME = "slave-scanner"


def get_builder(name):
    """Helper to return the builder given the slave for this request."""
    # Avoiding circular imports.
    from lp.buildmaster.interfaces.builder import IBuilderSet
    return getUtility(IBuilderSet)[name]


def assessFailureCounts(builder, fail_notes):
    """View builder/job failure_count and work out which needs to die.  """
    # builder.currentjob hides a complicated query, don't run it twice.
    # See bug 623281.
    current_job = builder.currentjob
    if current_job is None:
        job_failure_count = 0
    else:
        job_failure_count = current_job.specific_job.build.failure_count

    if builder.failure_count == job_failure_count and current_job is not None:
        # If the failure count for the builder is the same as the
        # failure count for the job being built, then we cannot
        # tell whether the job or the builder is at fault. The  best
        # we can do is try them both again, and hope that the job
        # runs against a different builder.
        current_job.reset()
        return

    if builder.failure_count > job_failure_count:
        # The builder has failed more than the jobs it's been
        # running.

        # Re-schedule the build if there is one.
        if current_job is not None:
            current_job.reset()

        # We are a little more tolerant with failing builders than
        # failing jobs because sometimes they get unresponsive due to
        # human error, flaky networks etc.  We expect the builder to get
        # better, whereas jobs are very unlikely to get better.
        if builder.failure_count >= Builder.FAILURE_THRESHOLD:
            # It's also gone over the threshold so let's disable it.
            builder.failBuilder(fail_notes)
    else:
        # The job is the culprit!  Override its status to 'failed'
        # to make sure it won't get automatically dispatched again,
        # and remove the buildqueue request.  The failure should
        # have already caused any relevant slave data to be stored
        # on the build record so don't worry about that here.
        builder.resetFailureCount()
        build_job = current_job.specific_job.build
        build_job.status = BuildStatus.FAILEDTOBUILD
        builder.currentjob.destroySelf()

        # N.B. We could try and call _handleStatus_PACKAGEFAIL here
        # but that would cause us to query the slave for its status
        # again, and if the slave is non-responsive it holds up the
        # next buildd scan.


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

    def __init__(self, builder_name, logger):
        self.builder_name = builder_name
        self.logger = logger

    def startCycle(self):
        """Scan the builder and dispatch to it or deal with failures."""
        self.loop = LoopingCall(self.singleCycle)
        self.stopping_deferred = self.loop.start(self.SCAN_INTERVAL)
        return self.stopping_deferred

    def stopCycle(self):
        """Terminate the LoopingCall."""
        self.loop.stop()

    def singleCycle(self):
        self.logger.debug("Scanning builder: %s" % self.builder_name)
        d = self.scan()

        d.addErrback(self._scanFailed)
        return d

    def _scanFailed(self, failure):
        """Deal with failures encountered during the scan cycle.

        1. Print the error in the log
        2. Increment and assess failure counts on the builder and job.
        """
        # Since this is a failure path, we could be in a broken
        # transaction.  Get us a fresh one.
        transaction.abort()

        # If we don't recognise the exception include a stack trace with
        # the error.
        error_message = failure.getErrorMessage()
        familiar_error = failure.check(
            BuildSlaveFailure, CannotBuild, BuildBehaviorMismatch,
            CannotResumeHost, BuildDaemonError, CannotFetchFile)
        if familiar_error:
            self.logger.info(
                "Scanning %s failed with: %s",
                self.builder_name, error_message)
        else:
            self.logger.info(
                "Scanning %s failed with: %s\n%s",
                self.builder_name, failure.getErrorMessage(),
                failure.getTraceback())

        # Decide if we need to terminate the job or fail the
        # builder.
        try:
            builder = get_builder(self.builder_name)
            transaction.commit()

            with DatabaseTransactionPolicy(read_only=False):
                builder.gotFailure()

                if builder.currentjob is None:
                    self.logger.info(
                        "Builder %s failed a probe, count: %s",
                        self.builder_name, builder.failure_count)
                else:
                    build_farm_job = builder.getCurrentBuildFarmJob()
                    build_farm_job.gotFailure()
                    self.logger.info(
                        "builder %s failure count: %s, "
                        "job '%s' failure count: %s",
                        self.builder_name,
                        builder.failure_count,
                        build_farm_job.title,
                        build_farm_job.failure_count)

                assessFailureCounts(builder, failure.getErrorMessage())
                transaction.commit()
        except:
            # Catastrophic code failure! Not much we can do.
            transaction.abort()
            self.logger.error(
                "Miserable failure when trying to examine failure counts:\n",
                exc_info=True)

    def checkCancellation(self, builder):
        """See if there is a pending cancellation request.

        If the current build is in status CANCELLING then terminate it
        immediately.

        :return: A deferred whose value is True if we cancelled the build.
        """
        if not builder.virtualized:
            return defer.succeed(False)
        buildqueue = self.builder.getBuildQueue()
        if not buildqueue:
            return defer.succeed(False)
        build = buildqueue.specific_job.build
        if build.status != BuildStatus.CANCELLING:
            return defer.succeed(False)

        def resume_done(ignored):
            return defer.succeed(True)

        self.logger.info("Cancelling build '%s'" % build.title)
        buildqueue.cancel()
        transaction.commit()
        d = builder.resumeSlaveHost()
        d.addCallback(resume_done)
        return d

    def scan(self):
        """Probe the builder and update/dispatch/collect as appropriate.

        There are several steps to scanning:

        1. If the builder is marked as "ok" then probe it to see what state
            it's in.  This is where lost jobs are rescued if we think the
            builder is doing something that it later tells us it's not,
            and also where the multi-phase abort procedure happens.
            See IBuilder.rescueIfLost, which is called by
            IBuilder.updateStatus().
        2. If the builder is still happy, we ask it if it has an active build
            and then either update the build in Launchpad or collect the
            completed build. (builder.updateBuild)
        3. If the builder is not happy or it was marked as unavailable
            mid-build, we need to reset the job that we thought it had, so
            that the job is dispatched elsewhere.
        4. If the builder is idle and we have another build ready, dispatch
            it.

        :return: A Deferred that fires when the scan is complete, whose
            value is A `BuilderSlave` if we dispatched a job to it, or None.
        """
        # We need to re-fetch the builder object on each cycle as the
        # Storm store is invalidated over transaction boundaries.
        self.builder = get_builder(self.builder_name)

        def status_updated(ignored):
            # See if we think there's an active build on the builder.
            buildqueue = self.builder.getBuildQueue()

            # Scan the slave and get the logtail, or collect the build if
            # it's ready.  Yes, "updateBuild" is a bad name.
            if buildqueue is not None:
                return self.builder.updateBuild(buildqueue)

        def build_updated(ignored):
            # If the builder is in manual mode, don't dispatch anything.
            if self.builder.manual:
                self.logger.debug(
                    '%s is in manual mode, not dispatching.',
                    self.builder.name)
                return

            # If the builder is marked unavailable, don't dispatch anything.
            # Additionaly, because builders can be removed from the pool at
            # any time, we need to see if we think there was a build running
            # on it before it was marked unavailable. In this case we reset
            # the build thusly forcing it to get re-dispatched to another
            # builder.

            return self.builder.isAvailable().addCallback(got_available)

        def got_available(available):
            if not available:
                job = self.builder.currentjob
                if job is not None and not self.builder.builderok:
                    self.logger.info(
                        "%s was made unavailable; resetting attached job.",
                        self.builder.name)
                    transaction.abort()
                    with DatabaseTransactionPolicy(read_only=False):
                        job.reset()
                        transaction.commit()
                return

            # See if there is a job we can dispatch to the builder slave.

            # XXX JeroenVermeulen 2011-10-11, bug=872112: The job's
            # failure count will be reset once the job has started
            # successfully.  Because of intervening commits, you may see
            # a build with a nonzero failure count that's actually going
            # to succeed later (and have a failure count of zero).  Or
            # it may fail yet end up with a lower failure count than you
            # saw earlier.
            d = self.builder.findAndStartJob()

            def job_started(candidate):
                if self.builder.currentjob is not None:
                    # After a successful dispatch we can reset the
                    # failure_count.
                    transaction.abort()
                    with DatabaseTransactionPolicy(read_only=False):
                        self.builder.resetFailureCount()
                        transaction.commit()
                    return self.builder.slave
                else:
                    return None
            return d.addCallback(job_started)

        def cancellation_checked(cancelled):
            if cancelled:
                return defer.succeed(None)
            d = self.builder.updateStatus(self.logger)
            d.addCallback(status_updated)
            d.addCallback(build_updated)
            return d

        if self.builder.builderok:
            d = self.checkCancellation(self.builder)
            d.addCallback(cancellation_checked)
        else:
            d = defer.succeed(None)
            d.addCallback(status_updated)
            d.addCallback(build_updated)

        return d


class NewBuildersScanner:
    """If new builders appear, create a scanner for them."""

    # How often to check for new builders, in seconds.
    SCAN_INTERVAL = 300

    def __init__(self, manager, clock=None):
        self.manager = manager
        # Use the clock if provided, it's so that tests can
        # advance it.  Use the reactor by default.
        if clock is None:
            clock = reactor
        self._clock = clock
        # Avoid circular import.
        from lp.buildmaster.interfaces.builder import IBuilderSet
        self.current_builders = [
            builder.name for builder in getUtility(IBuilderSet)]

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
        new_builders = self.checkForNewBuilders()
        self.manager.addScanForBuilders(new_builders)

    def checkForNewBuilders(self):
        """See if any new builders were added."""
        # Avoid circular import.
        from lp.buildmaster.interfaces.builder import IBuilderSet
        new_builders = set(
            builder.name for builder in getUtility(IBuilderSet))
        old_builders = set(self.current_builders)
        extra_builders = new_builders.difference(old_builders)
        self.current_builders.extend(extra_builders)
        return list(extra_builders)


class BuilddManager(service.Service):
    """Main Buildd Manager service class."""

    def __init__(self, clock=None):
        self.builder_slaves = []
        self.logger = self._setupLogger()
        self.new_builders_scanner = NewBuildersScanner(
            manager=self, clock=clock)
        self.transaction_policy = DatabaseTransactionPolicy(read_only=True)

    def _setupLogger(self):
        """Set up a 'slave-scanner' logger that redirects to twisted.

        Make it less verbose to avoid messing too much with the old code.
        """
        level = logging.INFO
        logger = logging.getLogger(BUILDD_MANAGER_LOG_NAME)

        # Redirect the output to the twisted log module.
        channel = logging.StreamHandler(log.StdioOnnaStick())
        channel.setLevel(level)
        channel.setFormatter(logging.Formatter('%(message)s'))

        logger.addHandler(channel)
        logger.setLevel(level)
        return logger

    def enterReadOnlyDatabasePolicy(self):
        """Set the database transaction policy to read-only.

        Any previously pending changes are committed first.
        """
        transaction.commit()
        self.transaction_policy.__enter__()

    def exitReadOnlyDatabasePolicy(self, *args):
        """Reset database transaction policy to the default read-write."""
        self.transaction_policy.__exit__(None, None, None)

    def startService(self):
        """Service entry point, called when the application starts."""
        # Avoiding circular imports.
        from lp.buildmaster.interfaces.builder import IBuilderSet

        self.enterReadOnlyDatabasePolicy()

        # Get a list of builders and set up scanners on each one.
        self.addScanForBuilders(
            [builder.name for builder in getUtility(IBuilderSet)])
        self.new_builders_scanner.scheduleScan()

        # Events will now fire in the SlaveScanner objects to scan each
        # builder.

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
        d.addCallback(self.exitReadOnlyDatabasePolicy)
        return d

    def addScanForBuilders(self, builders):
        """Set up scanner objects for the builders specified."""
        for builder in builders:
            slave_scanner = SlaveScanner(builder, self.logger)
            self.builder_slaves.append(slave_scanner)
            slave_scanner.startCycle()

        # Return the slave list for the benefit of tests.
        return self.builder_slaves

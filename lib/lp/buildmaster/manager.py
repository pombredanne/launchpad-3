# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Soyuz buildd slave manager logic."""

__metaclass__ = type

__all__ = [
    'BaseDispatchResult',
    'BuilddManager',
    'BUILDD_MANAGER_LOG_NAME',
    'FailDispatchResult',
    'ResetDispatchResult',
    'buildd_success_result_map',
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
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    BuildBehaviorMismatch,
    )
from lp.buildmaster.interfaces.builder import (
    BuildDaemonError,
    BuildSlaveFailure,
    CannotBuild,
    CannotResumeHost,
    )


BUILDD_MANAGER_LOG_NAME = "slave-scanner"


buildd_success_result_map = {
    'ensurepresent': True,
    'build': 'BuilderStatus.BUILDING',
    }


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
    build_job = current_job.specific_job.build

    if builder.failure_count == build_job.failure_count:
        # If the failure count for the builder is the same as the
        # failure count for the job being built, then we cannot
        # tell whether the job or the builder is at fault. The  best
        # we can do is try them both again, and hope that the job
        # runs against a different builder.
        current_job.reset()
        return

    if builder.failure_count > build_job.failure_count:
        # The builder has failed more than the jobs it's been
        # running, so let's disable it and re-schedule the build.
        builder.failBuilder(fail_notes)
        current_job.reset()
    else:
        # The job is the culprit!  Override its status to 'failed'
        # to make sure it won't get automatically dispatched again,
        # and remove the buildqueue request.  The failure should
        # have already caused any relevant slave data to be stored
        # on the build record so don't worry about that here.
        build_job.status = BuildStatus.FAILEDTOBUILD
        builder.currentjob.destroySelf()

        # N.B. We could try and call _handleStatus_PACKAGEFAIL here
        # but that would cause us to query the slave for its status
        # again, and if the slave is non-responsive it holds up the
        # next buildd scan.


class SlaveScanner:
    """A manager for a single builder."""

    SCAN_INTERVAL = 5

    def __init__(self, builder_name, logger):
        self.builder_name = builder_name
        self.logger = logger

    def startCycle(self):
        """Scan the builder and dispatch to it or deal with failures."""
        self.loop = LoopingCall(self._startCycle)
        self.stopping_deferred = self.loop.start(self.SCAN_INTERVAL)
        return self.stopping_deferred

    def _startCycle(self):
        # Same as _startCycle but the next cycle is not scheduled.  This
        # is so tests can initiate a single scan.
        self.logger.debug("Scanning builder: %s" % self.builder_name)
        d = self.scan()

        d.addErrback(self._scanFailed)
        return d

    def _scanFailed(self, failure):
        # Trap known exceptions and print a message without a
        # stack trace in that case, or if we don't know about it,
        # include the trace.

        # Paranoia.
        transaction.abort()

        error_message = failure.getErrorMessage()
        if failure.check(
            BuildSlaveFailure, CannotBuild, BuildBehaviorMismatch,
            CannotResumeHost, BuildDaemonError):
            self.logger.info("Scanning failed with: %s" % error_message)
        else:
            self.logger.info("Scanning failed with: %s\n%s" %
                (failure.getErrorMessage(), failure.getTraceback()))

        builder = get_builder(self.builder_name)

        # Decide if we need to terminate the job or fail the
        # builder.
        try:
            builder.gotFailure()
            builder.getCurrentBuildFarmJob().gotFailure()
            self.logger.info(
                "builder failure count: %s, job failure count: %s" % (
                    builder.failure_count,
                    builder.getCurrentBuildFarmJob().failure_count))
            assessFailureCounts(builder, failure.getErrorMessage())
            transaction.commit()
        except:
            # Catastrophic code failure! Not much we can do.
            self.logger.error(
                "Miserable failure when trying to examine failure counts:\n",
                exc_info=True)
            transaction.abort()

    def scan(self):
        """Probe the builder and update/dispatch/collect as appropriate.

        The whole method is wrapped in a transaction, but we do partial
        commits to avoid holding locks on tables.

        :return: A `BuilderSlave` if we dispatched a job to it, or None.
        """
        # We need to re-fetch the builder object on each cycle as the
        # Storm store is invalidated over transaction boundaries.

        self.builder = get_builder(self.builder_name)

        if self.builder.builderok:
            d = self.builder.updateStatus(self.logger)
        else:
            d = defer.succeed(None)

        def got_update_status(ignored):
            transaction.commit()

            # See if we think there's an active build on the builder.
            buildqueue = self.builder.getBuildQueue()

            # Scan the slave and get the logtail, or collect the build if
            # it's ready.  Yes, "updateBuild" is a bad name.
            if buildqueue is not None:
                return self.builder.updateBuild(buildqueue)

        def got_available(available):
            if not available:
                job = self.builder.currentjob
                if job is not None and not self.builder.builderok:
                    self.logger.info(
                        "%s was made unavailable, resetting attached "
                        "job" % self.builder.name)
                    job.reset()
                    transaction.commit()
                return

            # See if there is a job we can dispatch to the builder slave.

            d = self.builder.findAndStartJob()
            def job_started(candidate):
                if self.builder.currentjob is not None:
                    # After a successful dispatch we can reset the
                    # failure_count.
                    self.builder.resetFailureCount()
                    transaction.commit()
                    return self.builder.slave
                else:
                    return None
            return d.addCallback(job_started)

        def got_update_build(ignored):
            transaction.commit()

            # If the builder is in manual mode, don't dispatch anything.
            if self.builder.manual:
                self.logger.debug(
                    '%s is in manual mode, not dispatching.' %
                    self.builder.name)
                return

            # If the builder is marked unavailable, don't dispatch anything.
            # Additionaly, because builders can be removed from the pool at
            # any time, we need to see if we think there was a build running
            # on it before it was marked unavailable. In this case we reset
            # the build thusly forcing it to get re-dispatched to another
            # builder.

            return self.builder.isAvailable().addCallback(got_available)

        d.addCallback(got_update_status)
        d.addCallback(got_update_build)
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
        return list(extra_builders)


class BuilddManager(service.Service):
    """Main Buildd Manager service class."""

    def __init__(self, clock=None):
        self.builder_slaves = []
        self.logger = self._setupLogger()
        self.new_builders_scanner = NewBuildersScanner(
            manager=self, clock=clock)

    def _setupLogger(self):
        """Setup a 'slave-scanner' logger that redirects to twisted.

        It is going to be used locally and within the thread running
        the scan() method.

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

    def startService(self):
        """Service entry point, called when the application starts."""

        # Get a list of builders and set up scanners on each one.

        # Avoiding circular imports.
        from lp.buildmaster.interfaces.builder import IBuilderSet
        builder_set = getUtility(IBuilderSet)
        builders = [builder.name for builder in builder_set]
        self.addScanForBuilders(builders)
        self.new_builders_scanner.scheduleScan()

        # Events will now fire in the SlaveScanner objects to scan each
        # builder.

    def stopService(self):
        """Callback for when we need to shut down."""
        # All the SlaveScanner objects need to be halted gracefully.
        deferreds = [slave.stopping_deferred for slave in self.builder_slaves]
        deferreds.append(self.new_builders_scanner.stopping_deferred)

        self.new_builders_scanner.loop.stop()
        for slave in self.builder_slaves:
            slave.loop.stop()

        # The 'stopping_deferred's are called back when the loops are
        # stopped, so we can wait on them all at once here before
        # exiting.
        d = defer.DeferredList(deferreds, consumeErrors=True)
        return d

    def addScanForBuilders(self, builders):
        """Set up scanner objects for the builders specified."""
        for builder in builders:
            slave_scanner = SlaveScanner(builder, self.logger)
            self.builder_slaves.append(slave_scanner)
            slave_scanner.startCycle()

        # Return the slave list for the benefit of tests.
        return self.builder_slaves

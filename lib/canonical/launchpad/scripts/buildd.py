# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Buildd cronscript classes """

__metaclass__ = type

__all__ = [
    'QueueBuilder',
    'RetryDepwait',
    'SlaveScanner',
    ]

from zope.component import getUtility

from canonical.archivepublisher.debversion import Version
from canonical.buildmaster.master import BuilddMaster
from canonical.launchpad.interfaces import (
    DistroSeriesStatus, IBuilderSet, IBuildSet, IDistributionSet,
    IDistroArchSeriesSet, NotFoundError)
from canonical.launchpad.scripts.base import (
    LaunchpadCronScript, LaunchpadScriptFailure)


class QueueBuilder(LaunchpadCronScript):

    def add_my_options(self):
        self.parser.add_option(
            "-n", "--dry-run", action="store_true",
            dest="dryrun", metavar="DRY_RUN", default=False,
            help="Whether to treat this as a dry-run or not.")

    def main(self):
        """Invoke rebuildQueue.

        Check if the cron.daily is running, quietly exits if true.
        Force isolation level to ISOLATION_LEVEL_READ_COMMITTED.
        Deals with the current transaction according the dry-run option.
        """
        if self.args:
            raise LaunchpadScriptFailure("Unhandled arguments %r" % self.args)

        # In order to avoid the partial commits inside BuilddMaster
        # to happen we pass a FakeZtm instance if dry-run mode is selected.
        class _FakeZTM:
            """A fake transaction manager."""
            def commit(self):
                pass

        if self.options.dryrun:
            self.logger.info("Dry run: changes will not be committed.")
            self.txn = _FakeZTM()

        self.rebuildQueue()
        self.txn.commit()

    def rebuildQueue(self):
        """Look for and initialise new build jobs."""

        self.logger.info("Rebuilding Build Queue.")
        buildMaster = BuilddMaster(self.logger, self.txn)

        # For every distroarchseries we can find; put it into the build master
        distroserieses = set()
        for archseries in getUtility(IDistroArchSeriesSet):
            distroserieses.add(archseries.distroseries)
            buildMaster.addDistroArchSeries(archseries)

        # For each distroseries we care about; scan for sourcepackagereleases
        # with no build associated with the distroarchserieses we're
        # interested in
        for distroseries in sorted(distroserieses,
            key=lambda x: (x.distribution, Version(x.version))):
            buildMaster.createMissingBuilds(distroseries)

        # For each build record in NEEDSBUILD, ensure it has a
        # buildqueue entry
        buildMaster.addMissingBuildQueueEntries()

        # Re-score the NEEDSBUILD properly
        buildMaster.scoreCandidates()


class RetryDepwait(LaunchpadCronScript):

    def add_my_options(self):
        self.parser.add_option(
            "-d", "--distribution", default="ubuntu",
            help="Context distribution.")

        self.parser.add_option(
            "-n", "--dry-run",
            dest="dryrun", action="store_true", default=False,
            help="Whether or not to commit the transaction.")

    def main(self):
        """Retry all builds that do not fit in MANUALDEPWAIT.

        Iterate over all supported series in the given distribution and
        their architectures with existent chroots and update all builds
        found in MANUALDEPWAIT status.
        """
        if self.args:
            raise LaunchpadScriptFailure("Unhandled arguments %r" % self.args)

        distribution_set = getUtility(IDistributionSet)
        try:
            distribution = distribution_set[self.options.distribution]
        except NotFoundError:
            raise LaunchpadScriptFailure(
                "Could not find distribution: %s" % self.options.distribution)

        # Iterate over all supported distroarchseries with available chroot.
        build_set = getUtility(IBuildSet)
        for distroseries in distribution:
            if distroseries.status == DistroSeriesStatus.OBSOLETE:
                self.logger.debug(
                    "Skipping obsolete distroseries: %s" % distroseries.title)
                continue
            for distroarchseries in distroseries.architectures:
                self.logger.info("Processing %s" % distroarchseries.title)
                if not distroarchseries.getChroot:
                    self.logger.debug("Chroot not found")
                    continue
                build_set.retryDepWaiting(distroarchseries)

        # XXX cprov 20071122:  LaunchpadScript should provide some
        # infrastructure for dry-run operations and not simply rely
        # on the transaction being discarded by the garbage-collector.
        # See further information in bug #165200.
        if not self.options.dryrun:
            self.logger.info('Commiting the transaction.')
            self.txn.commit()


class SlaveScanner(LaunchpadCronScript):

    def main(self):
        if self.args:
            raise LaunchpadScriptFailure(
                "Unhandled arguments %s" % repr(self.args))

        builder_set = getUtility(IBuilderSet)
        buildMaster = builder_set.pollBuilders(self.logger, self.txn)

        self.logger.info("Dispatching Jobs.")

        for builder in builder_set:
            self.logger.info("Processing: %s" % builder.name)
            # XXX cprov 2007-11-09: we don't support manual dispatching
            # yet. Once we support it this clause should be removed.
            if builder.manual:
                self.logger.warn('builder is in manual state. Ignored.')
                continue
            if not builder.is_available:
                self.logger.warn('builder is not available. Ignored.')
                continue
            candidate = builder.findBuildCandidate()
            if candidate is None:
                self.logger.debug(
                    "No candidates available for builder.")
                continue
            builder.dispatchBuildCandidate(candidate)
            self.txn.commit()

        self.logger.info("Slave Scan Process Finished.")

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
from lp.soyuz.interfaces.build import IBuildSet
from lp.soyuz.interfaces.builder import IBuilderSet
from canonical.launchpad.interfaces.launchpad import NotFoundError
from lp.services.scripts.base import (
    LaunchpadCronScript, LaunchpadScriptFailure)
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.distroseries import DistroSeriesStatus

# XXX cprov 2009-04-16: This function should live in
# lp.registry.interfaces.distroseries. It cannot be done right now
# because we haven't decided if archivepublisher.debversion will be
# released as FOSS yet.
def distroseries_sort_key(series):
    """Sort `DistroSeries` by version.

    See `canonical.archivepublisher.debversion.Version` for more
    information.
    """
    return Version(series.version)


class QueueBuilder(LaunchpadCronScript):

    def add_my_options(self):
        self.parser.add_option(
            "-n", "--dry-run", action="store_true",
            dest="dryrun", metavar="DRY_RUN", default=False,
            help="Whether to treat this as a dry-run or not.")

        self.parser.add_option(
            "--score-only", action="store_true",
            dest="score_only", default=False,
            help="Skip build creation, only score existing builds.")

        self.parser.add_option(
            "-d", "--distribution", default="ubuntu",
            help="Context distribution.")

        self.parser.add_option(
            '-s', '--suite', metavar='SUITE', dest='suite',
            action='append', type='string', default=[],
            help='The suite to process')

    def main(self):
        """Use BuildMaster for processing the build queue.

        Callers my define a specific set of distroseries to be processed
        and also decide whether or not the queue-rebuild (expensive
        procedure) should be executed.

        Deals with the current transaction according to the dry-run option.
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

        sorted_distroseries = self.calculateDistroseries()
        buildMaster = BuilddMaster(self.logger, self.txn)
        # Initialize BuilddMaster with the relevant architectures.
        # it's needed even for 'score-only' mode.
        for series in sorted_distroseries:
            for archseries in series.architectures:
                buildMaster.addDistroArchSeries(archseries)

        if not self.options.score_only:
            # For each distroseries we care about, scan for
            # sourcepackagereleases with no build associated
            # with the distroarchserieses we're interested in.
            self.logger.info("Rebuilding build queue.")
            for distroseries in sorted_distroseries:
                buildMaster.createMissingBuilds(distroseries)

        # Ensure all NEEDSBUILD builds have a buildqueue entry
        # and re-score them.
        buildMaster.addMissingBuildQueueEntries()
        buildMaster.scoreCandidates()

        self.txn.commit()

    def calculateDistroseries(self):
        """Return an ordered list of distroseries for the given arguments."""
        distribution = getUtility(IDistributionSet).getByName(
            self.options.distribution)
        if distribution is None:
            raise LaunchpadScriptFailure(
                "Could not find distribution: %s" % self.options.distribution)

        if len(self.options.suite) == 0:
            return sorted(distribution.serieses, key=distroseries_sort_key)

        distroseries_set = set()
        for suite in self.options.suite:
            try:
                distroseries, pocket = distribution.getDistroSeriesAndPocket(
                    suite)
            except NotFoundError, err:
                raise LaunchpadScriptFailure("Could not find suite %s" % err)
            distroseries_set.add(distroseries)

        return sorted(distroseries_set, key=distroseries_sort_key)


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

# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Buildd cronscript classes """

__metaclass__ = type

__all__ = [
    'QueueBuilder',
    'RetryDepwait',
    ]

from zope.component import getUtility

from canonical.config import config
from lp.app.errors import NotFoundError
from lp.archivepublisher.debversion import Version
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.series import SeriesStatus
from lp.services.scripts.base import (
    LaunchpadCronScript,
    LaunchpadScriptFailure,
    )
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuildSet
from lp.soyuz.pas import BuildDaemonPackagesArchSpecific


# XXX cprov 2009-04-16: This function should live in
# lp.registry.interfaces.distroseries. It cannot be done right now
# because we haven't decided if archivepublisher.debversion will be
# released as FOSS yet.
def distroseries_sort_key(series):
    """Sort `DistroSeries` by version.

    See `lp.archivepublisher.debversion.Version` for more
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

        # In dry-run mode we use a fake transaction manager with a no-op
        # commit(), so we avoid partial commits that are performed by some of
        # our methods.
        class _FakeZTM:
            """A fake transaction manager."""

            def commit(self):
                pass

        if self.options.dryrun:
            self.logger.info("Dry run: changes will not be committed.")
            self.txn = _FakeZTM()

        sorted_distroseries = self.calculateDistroseries()
        archseries = []
        # Initialize the relevant architectures (those with chroots).
        # it's needed even for 'score-only' mode.
        for series in sorted_distroseries:
            for das in series.architectures:
                if das.getChroot():
                    archseries.append(das)

        if not self.options.score_only:
            # For each distroseries we care about, scan for
            # sourcepackagereleases with no build associated
            # with the distroarchseries we're interested in.
            self.logger.info("Rebuilding build queue.")
            for distroseries in sorted_distroseries:
                self.createMissingBuilds(distroseries)

        # Ensure all NEEDSBUILD builds have a buildqueue entry
        # and re-score them.
        self.addMissingBuildQueueEntries(archseries)
        self.scoreCandidates(archseries)

        self.txn.commit()

    def createMissingBuilds(self, distroseries):
        """Ensure that each published package is completely built."""
        self.logger.info("Processing %s" % distroseries.name)
        # Do not create builds for distroseries with no nominatedarchindep
        # they can't build architecture independent packages properly.
        if not distroseries.nominatedarchindep:
            self.logger.debug(
                "No nominatedarchindep for %s, skipping" % distroseries.name)
            return

        # Listify the architectures to avoid hitting this MultipleJoin
        # multiple times.
        distroseries_architectures = list(distroseries.architectures)
        if not distroseries_architectures:
            self.logger.debug(
                "No architectures defined for %s, skipping"
                % distroseries.name)
            return

        architectures_available = list(distroseries.buildable_architectures)
        if not architectures_available:
            self.logger.debug(
                "Chroots missing for %s, skipping" % distroseries.name)
            return

        self.logger.info(
            "Supported architectures: %s" %
            " ".join(arch_series.architecturetag
                     for arch_series in architectures_available))

        pas_verify = BuildDaemonPackagesArchSpecific(
            config.builddmaster.root, distroseries)

        sources_published = distroseries.getSourcesPublishedForAllArchives()
        self.logger.info(
            "Found %d source(s) published." % sources_published.count())

        for pubrec in sources_published:
            builds = pubrec.createMissingBuilds(
                architectures_available=architectures_available,
                pas_verify=pas_verify, logger=self.logger)
            if len(builds) > 0:
                self.txn.commit()

    def addMissingBuildQueueEntries(self, archseries):
        """Create missing Buildd Jobs. """
        self.logger.info("Scanning for build queue entries that are missing")

        buildset = getUtility(IBinaryPackageBuildSet)
        builds = buildset.getPendingBuildsForArchSet(archseries)

        if not builds:
            return

        for build in builds:
            if not build.buildqueue_record:
                name = build.source_package_release.name
                version = build.source_package_release.version
                tag = build.distro_arch_series.architecturetag
                self.logger.debug(
                    "Creating buildqueue record for %s (%s) on %s"
                    % (name, version, tag))
                build.queueBuild()

        self.txn.commit()

    def scoreCandidates(self, archseries):
        """Iterate over the pending buildqueue entries and re-score them."""
        if not archseries:
            self.logger.info("No architecture found to rescore.")
            return

        # Get the current build job candidates.
        candidates = getUtility(IBinaryPackageBuildSet).calculateCandidates(
            archseries)

        self.logger.info("Found %d build in NEEDSBUILD state. Rescoring"
                         % candidates.count())

        for job in candidates:
            uptodate_build = getUtility(
                IBinaryPackageBuildSet).getByQueueEntry(job)
            if uptodate_build.status != BuildStatus.NEEDSBUILD:
                continue
            job.score()

    def calculateDistroseries(self):
        """Return an ordered list of distroseries for the given arguments."""
        distribution = getUtility(IDistributionSet).getByName(
            self.options.distribution)
        if distribution is None:
            raise LaunchpadScriptFailure(
                "Could not find distribution: %s" % self.options.distribution)

        if len(self.options.suite) == 0:
            return sorted(distribution.series, key=distroseries_sort_key)

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
        build_set = getUtility(IBinaryPackageBuildSet)
        for distroseries in distribution:
            if distroseries.status == SeriesStatus.OBSOLETE:
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

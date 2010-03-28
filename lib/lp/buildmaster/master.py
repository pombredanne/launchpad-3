# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

#Authors: Daniel Silverstone <daniel.silverstone@canonical.com>
#         Celso Providelo <celso.providelo@canonical.com>

"""Common code for Buildd scripts

Module used by buildd-queue-builder.py and buildd-slave-scanner.py
cronscripts.
"""

__metaclass__ = type


import logging

from zope.component import getUtility

from canonical.buildd.utils import notes
from canonical.config import config
from canonical.librarian.interfaces import ILibrarianClient
from lp.archivepublisher.utils import process_in_batches
from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.buildmaster.interfaces.buildqueue import IBuildQueueSet
from lp.buildmaster.buildergroup import BuilderGroup
from lp.soyuz.interfaces.build import IBuildSet
from lp.soyuz.pas import BuildDaemonPackagesArchSpecific


class BuilddMaster:
    """Canonical autobuilder master, toolkit and algorithms.

    This class is in the process of being deprecated in favour of the regular
    content classes.
    """
    # XXX cprov 2007-06-15: Please do not extend this class except as
    # required to move more logic into the content classes. A new feature
    # should be modeled directly in IBuilder.

    def __init__(self, logger, tm):
        self._logger = logger
        self._tm = tm
        self.librarian = getUtility(ILibrarianClient)
        self._archseries = {}
        self._logger.debug("Buildd Master has been initialised")

    def commit(self):
        self._tm.commit()

    def addDistroArchSeries(self, distroarchseries):
        """Setting up a workable DistroArchSeries for this session."""
        self._logger.debug("Adding DistroArchSeries %s/%s/%s"
                          % (distroarchseries.distroseries.distribution.name,
                             distroarchseries.distroseries.name,
                             distroarchseries.architecturetag))

        # Is there a chroot for this archseries?
        if distroarchseries.getChroot():
            # Fill out the contents.
            self._archseries.setdefault(distroarchseries, {})

    def setupBuilders(self, archseries):
        """Setting up a group of builder slaves for a given DistroArchSeries.

        Use the annotation utility to store a BuilderGroup instance
        keyed by the the DistroArchSeries.processorfamily in the
        global registry 'notes' and refer to this 'note' in the private
        attribute '_archseries' keyed by the given DistroArchSeries
        and the label 'builders'. This complicated arrangement enables us
        to share builder slaves between different DistroArchRelases since
        their processorfamily values are the same (compatible processors).
        """
        # Determine the builders for this distroarchseries...
        if archseries not in self._archseries:
            # Avoid entering in the huge loop if we don't find at least
            # one architecture for which we can build on.
            self._logger.debug(
                "Chroot missing for %s/%s/%s, skipping"
                % (archseries.distroseries.distribution.name,
                   archseries.distroseries.name,
                   archseries.architecturetag))
            return

        # query the global annotation registry and verify if
        # we have already done the builder checks for the
        # processor family in question. if it's already done
        # simply refer to that information in the _archseries
        # attribute.
        if 'builders' not in notes[archseries.processorfamily]:

            # setup a BuilderGroup object
            info = "builders.%s" % archseries.processorfamily.name
            builderGroup = BuilderGroup(self.getLogger(info), self._tm)

            # check the available slaves for this archseries
            builderGroup.checkAvailableSlaves(archseries)

            # annotate the group of builders for the
            # DistroArchSeries.processorfamily in question and the
            # label 'builders'
            notes[archseries.processorfamily]["builders"] = builderGroup

        # consolidate the annotation for the architecture release
        # in the private attribute _archreleases
        self._archseries[archseries]["builders"] = \
            notes[archseries.processorfamily]["builders"]

    def createMissingBuilds(self, distroseries):
        """Ensure that each published package is completly built."""
        self._logger.info("Processing %s" % distroseries.name)
        # Do not create builds for distroseries with no nominatedarchindep
        # they can't build architecture independent packages properly.
        if not distroseries.nominatedarchindep:
            self._logger.debug(
                "No nominatedarchindep for %s, skipping" % distroseries.name)
            return

        # Listify the architectures to avoid hitting this MultipleJoin
        # multiple times.
        distroseries_architectures = list(distroseries.architectures)
        if not distroseries_architectures:
            self._logger.debug(
                "No architectures defined for %s, skipping"
                % distroseries.name)
            return

        architectures_available = list(distroseries.enabled_architectures)
        if not architectures_available:
            self._logger.debug(
                "Chroots missing for %s, skipping" % distroseries.name)
            return

        self._logger.info(
            "Supported architectures: %s" %
            " ".join(arch_series.architecturetag
                     for arch_series in architectures_available))

        pas_verify = BuildDaemonPackagesArchSpecific(
            config.builddmaster.root, distroseries)

        sources_published = distroseries.getSourcesPublishedForAllArchives()
        self._logger.info(
            "Found %d source(s) published." % sources_published.count())

        def process_source(pubrec):
            builds = pubrec.createMissingBuilds(
                architectures_available=architectures_available,
                pas_verify=pas_verify, logger=self._logger)
            if len(builds) > 0:
                self.commit()

        process_in_batches(
            sources_published, process_source, self._logger,
            minimum_chunk_size=1000)

    def addMissingBuildQueueEntries(self):
        """Create missing Buildd Jobs. """
        self._logger.info("Scanning for build queue entries that are missing")

        buildset = getUtility(IBuildSet)
        builds = buildset.getPendingBuildsForArchSet(self._archseries)

        if not builds:
            return

        for build in builds:
            if not build.buildqueue_record:
                name = build.sourcepackagerelease.name
                version = build.sourcepackagerelease.version
                tag = build.distroarchseries.architecturetag
                self._logger.debug(
                    "Creating buildqueue record for %s (%s) on %s"
                    % (name, version, tag))
                build.queueBuild()

        self.commit()

    def scanActiveBuilders(self):
        """Collect informations/results of current build jobs."""

        queueItems = getUtility(IBuildQueueSet).getActiveBuildJobs()

        self._logger.debug(
            "scanActiveBuilders() found %d active build(s) to check"
            % queueItems.count())

        for job in queueItems:
            job.builder.updateBuild(job)
            self.commit()

    def getLogger(self, subname=None):
        """Return the logger instance with specific prefix"""
        if subname is None:
            return self._logger
        return logging.getLogger("%s.%s" % (self._logger.name, subname))

    def scoreCandidates(self):
        """Iterate over the pending buildqueue entries and re-score them."""
        if not self._archseries:
            self._logger.info("No architecture found to rescore.")
            return

        # Get the current build job candidates.
        archseries = self._archseries.keys()
        bqset = getUtility(IBuildQueueSet)
        candidates = bqset.calculateCandidates(archseries)

        self._logger.info("Found %d build in NEEDSBUILD state. Rescoring"
                          % candidates.count())

        for job in candidates:
            uptodate_build = getUtility(IBuildSet).getByQueueEntry(job)
            if uptodate_build.buildstate != BuildStatus.NEEDSBUILD:
                continue
            job.score()

        self.commit()

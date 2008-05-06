#Copyright Canonical Limited 2005-2004
#Authors: Daniel Silverstone <daniel.silverstone@canonical.com>
#         Celso Providelo <celso.providelo@canonical.com>

"""Common code for Buildd scripts

Module used by buildd-queue-builder.py and buildd-slave-scanner.py
cronscripts.
"""

__metaclass__ = type


import logging
import operator

from zope.component import getUtility

from canonical.librarian.interfaces import ILibrarianClient

from canonical.launchpad.interfaces import (
    ArchivePurpose, BuildStatus, IBuildQueueSet, IBuildSet)

from canonical.buildd.utils import notes
from canonical.buildmaster.pas import BuildDaemonPackagesArchSpecific
from canonical.buildmaster.buildergroup import BuilderGroup
from canonical.config import config


def determineArchitecturesToBuild(pubrec, legal_archserieses,
                                  distroseries, pas_verify=None):
    """Return a list of architectures for which this publication should build.

    This function answers the question: given a publication, what
    architectures should we build it for? It takes a set of legal
    distroarchserieses and the distribution series for which we are
    building, and optionally a BuildDaemonPackagesArchSpecific
    (informally known as 'P-a-s') instance.

    The P-a-s component contains a list of forbidden architectures for
    each source package, which should be respected regardless of which
    architectures have been requested in the source package metadata,
    for instance:

      * 'aboot' should only build on powerpc
      * 'mozilla-firefox' should not build on sparc

    This black/white list is an optimization to suppress temporarily
    known-failures build attempts and thus saving build-farm time.

    For PPA publications we only consider architectures supported by PPA
    subsystem (`DistroArchSeries`.supports_virtualized flag) and P-a-s is turned
    off to give the users the chance to test their fixes for upstream
    problems.

    :param: pubrec: `ISourcePackagePublishingHistory` representing the
        source publication.
    :param: legal_archserieses: a list of all initialized `DistroArchSeries`
        to be considered.
    :param: distroseries: the context `DistroSeries`.
    :param: pas_verify: optional P-a-s verifier object/component.
    :return: a list of `DistroArchSeries` for which the source publication in
        question should be built.
    """
    hint_string = pubrec.sourcepackagerelease.architecturehintlist

    assert hint_string, 'Missing arch_hint_list'

    # Ignore P-a-s for PPA publications.
    if pubrec.archive.purpose == ArchivePurpose.PPA:
        pas_verify = None

    # The 'PPA supported' flag only applies to virtualized archives
    if pubrec.archive.require_virtualized:
        legal_archserieses = [
            arch for arch in legal_archserieses if arch.supports_virtualized]
        # Cope with no virtualization support at all. It usually happens when
        # a distroseries is created and initialized, by default no
        # architecture supports its. Distro-team might take some time to
        # decide which architecture will be allowed for PPAs and queue-builder
        # will continue to work meanwhile.
        if not legal_archserieses:
            return []

    legal_arch_tags = set(arch.architecturetag for arch in legal_archserieses)

    if hint_string == 'any':
        package_tags = legal_arch_tags
    elif hint_string == 'all':
        nominated_arch = distroseries.nominatedarchindep
        assert nominated_arch in legal_archserieses, (
            'nominatedarchindep is not present in legal_archseries')
        package_tags = set([nominated_arch.architecturetag])
    else:
        my_archs = hint_string.split()
        # Allow any-foo or linux-foo to mean foo. See bug 73761.
        my_archs = [arch.replace("any-", "") for arch in my_archs]
        my_archs = [arch.replace("linux-", "") for arch in my_archs]
        my_archs = set(my_archs)
        package_tags = my_archs.intersection(legal_arch_tags)

    if pas_verify:
        build_tags = set()
        for tag in package_tags:
            sourcepackage_name = pubrec.sourcepackagerelease.name
            if sourcepackage_name in pas_verify.permit:
                permitted = pas_verify.permit[sourcepackage_name]
                if tag not in permitted:
                    continue
            build_tags.add(tag)
    else:
        build_tags = package_tags

    sorted_archserieses = sorted(legal_archserieses,
                                 key=operator.attrgetter('architecturetag'))
    return [arch for arch in sorted_archserieses
            if arch.architecturetag in build_tags]


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
        self._archserieses = {}
        self._logger.info("Buildd Master has been initialised")

    def commit(self):
        self._tm.commit()

    def addDistroArchSeries(self, distroarchseries):
        """Setting up a workable DistroArchSeries for this session."""
        self._logger.info("Adding DistroArchSeries %s/%s/%s"
                          % (distroarchseries.distroseries.distribution.name,
                             distroarchseries.distroseries.name,
                             distroarchseries.architecturetag))

        # Is there a chroot for this archseries?
        if distroarchseries.getChroot():
            # Fill out the contents.
            self._archserieses.setdefault(distroarchseries, {})

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
        if archseries not in self._archserieses:
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
        # simply refer to that information in the _archserieses
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
        self._archserieses[archseries]["builders"] = \
            notes[archseries.processorfamily]["builders"]

    def createMissingBuilds(self, distroseries):
        """Ensure that each published package is completly built."""
        self._logger.debug("Processing %s" % distroseries.name)
        # Do not create builds for distroserieses with no nominatedarchindep
        # they can't build architecture independent packages properly.
        if not distroseries.nominatedarchindep:
            self._logger.debug(
                "No nominatedarchindep for %s, skipping" % distroseries.name)
            return

        # listify to avoid hitting this MultipleJoin multiple times
        distroseries_architectures = list(distroseries.architectures)
        if not distroseries_architectures:
            self._logger.debug(
                "No architectures defined for %s, skipping"
                % distroseries.name)
            return

        architectures_available = [
            arch for arch in distroseries.architectures
            if arch.getPocketChroot() is not None]

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

        for pubrec in sources_published:
            build_archs = determineArchitecturesToBuild(
                pubrec, architectures_available, distroseries, pas_verify)
            for arch in build_archs:
                build = pubrec.createMissingBuildForArchitecture(arch)
                if build is None:
                    continue
                self._logger.debug(
                    "Created %s [%d] in %s (%d)" % (
                        build.title, build.id, build.archive.title,
                        build.buildqueue_record.lastscore))
                self.commit()

    def addMissingBuildQueueEntries(self):
        """Create missing Buildd Jobs. """
        self._logger.info("Scanning for build queue entries that are missing")

        buildset = getUtility(IBuildSet)
        builds = buildset.getPendingBuildsForArchSet(self._archserieses)

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
                build.createBuildQueueEntry()

        self.commit()

    def scanActiveBuilders(self):
        """Collect informations/results of current build jobs."""

        queueItems = getUtility(IBuildQueueSet).getActiveBuildJobs()

        self._logger.debug(
            "scanActiveBuilders() found %d active build(s) to check"
            % queueItems.count())

        for job in queueItems:
            proc = job.archseries.processorfamily
            try:
                builders = notes[proc]["builders"]
            except KeyError:
                continue
            builders.updateBuild(job)

    def getLogger(self, subname=None):
        """Return the logger instance with specific prefix"""
        if subname is None:
            return self._logger
        return logging.getLogger("%s.%s" % (self._logger.name, subname))

    def scoreCandidates(self):
        """Iterate over the pending buildqueue entries and re-score them."""
        if not self._archserieses:
            self._logger.info("No architecture found to rescore.")
            return

        # Get the current build job candidates.
        archseries = self._archserieses.keys()
        bqset = getUtility(IBuildQueueSet)
        candidates = bqset.calculateCandidates(archseries)

        self._logger.info("Found %d build in NEEDSBUILD state. Rescoring"
                          % candidates.count())

        for job in candidates:
            uptodate_build = getUtility(IBuildSet).getByBuildID(job.build.id)
            if uptodate_build.buildstate != BuildStatus.NEEDSBUILD:
                continue
            job.score()

        self.commit()

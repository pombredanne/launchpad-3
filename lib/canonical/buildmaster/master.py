#Copyright Canonical Limited 2005-2004
#Authors: Daniel Silverstone <daniel.silverstone@canonical.com>
#         Celso Providelo <celso.providelo@canonical.com>

"""Common code for Buildd scripts

Module used by buildd-queue-builder.py and buildd-slave-scanner.py
cronscripts.
"""

__metaclass__ = type


import apt_pkg
import logging
import operator

from zope.component import getUtility

from canonical.librarian.interfaces import ILibrarianClient

from canonical.launchpad.interfaces import (
    ArchivePurpose, BuildStatus, BuildSlaveFailure, CannotBuild,
    IBuildQueueSet, IBuildSet
    )

from canonical.lp import dbschema
from canonical.config import config

from canonical.buildd.utils import notes
from canonical.buildmaster.pas import BuildDaemonPackagesArchSpecific
from canonical.buildmaster.buildergroup import BuilderGroup


# builddmaster shared lockfile
builddmaster_lockfilename = 'build-master'

# Constants used in build scoring
SCORE_SATISFIEDDEP = 5
SCORE_UNSATISFIEDDEP = 10

# this dict maps the package version relationship syntax in lambda
# functions which returns boolean according the results of
# apt_pkg.VersionCompare function (see the order above).
# For further information about pkg relationship syntax see:
#
# http://www.debian.org/doc/debian-policy/ch-relationships.html
#
version_relation_map = {
    # any version is acceptable if no relationship is given
    '': lambda x: True,
    # stricly later
    '>>': lambda x: x == 1,
    # later or equal
    '>=': lambda x: x >= 0,
    # stricly equal
    '=': lambda x: x == 0,
    # earlier or equal
    '<=': lambda x: x <= 0,
    # strictly ealier
    '<<': lambda x: x == -1
}


def determineArchitecturesToBuild(pubrec, legal_archserieses,
                                  distroseries, pas_verify=None):
    """Return a list of DistroArchSeries for which this publication
    should build.

    This function answers the question: given a publication, what
    architectures should we build it for? It takes a set of legal
    distroarchserieses and the distribution series for which we are
    buiilding, and optionally a BuildDaemonPackagesArchSpecific
    instance.
    """
    hint_string = pubrec.sourcepackagerelease.architecturehintlist

    assert hint_string, 'Missing arch_hint_list'

    legal_arch_tags = set(arch.architecturetag
                          for arch in legal_archserieses)

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
        # apt_pkg requires InitSystem to get VersionCompare working properly
        apt_pkg.InitSystem()
        self._logger.info("Buildd Master has been initialised")

    def commit(self):
        self._tm.commit()

    def addDistroArchSeries(self, distroarchseries):
        """Setting up a workable DistroArchSeries for this session."""
        self._logger.info("Adding DistroArchSeries %s/%s/%s"
                          % (distroarchseries.distroseries.distribution.name,
                             distroarchseries.distroseries.name,
                             distroarchseries.architecturetag))

        # check ARCHSERIES across available pockets
        for pocket in dbschema.PackagePublishingPocket.items:
            if distroarchseries.getChroot(pocket):
                # Fill out the contents
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

        registered_arch_ids = set(dar.id for dar in self._archserieses.keys())
        series_arch_ids = set(dar.id for dar in distroseries_architectures)
        legal_arch_ids = series_arch_ids.intersection(registered_arch_ids)
        legal_archs = [dar for dar in distroseries_architectures
                       if dar.id in legal_arch_ids]
        if not legal_archs:
            self._logger.debug(
                "Chroots missing for %s, skipping" % distroseries.name)
            return

        self._logger.info("Supported architectures: %s" %
                          " ".join(a.architecturetag for a in legal_archs))

        pas_verify = BuildDaemonPackagesArchSpecific(
            config.builddmaster.root, distroseries)

        sources_published = distroseries.getSourcesPublishedForAllArchives()
        self._logger.info(
            "Found %d source(s) published." % sources_published.count())

        for pubrec in sources_published:
            # XXX cprov 2007-07-11 bug=129491: Fix me please, 'ppa_archtags'
            # should be modeled as DistroArchSeries.ppa_supported.
            if pubrec.archive.purpose == ArchivePurpose.PPA:
                ppa_archtags = ('i386', 'amd64')
                local_archs = [
                    distro_arch_series for distro_arch_series in legal_archs
                    if distro_arch_series.architecturetag in ppa_archtags]
            else:
                local_archs = legal_archs

            build_archs = determineArchitecturesToBuild(
                pubrec, local_archs, distroseries, pas_verify)

            self._createMissingBuildsForPublication(pubrec, build_archs)

        self.commit()

    def _createMissingBuildsForPublication(self, pubrec, build_archs):
        """Create new Build record for the requested archseries.

        It verifies if the requested build is already inserted before
        creating a new one.
        The Build record is created for the archseries 'default_processor'.
        """
        header = ("build record %s-%s for '%s' " %
                  (pubrec.sourcepackagerelease.name,
                   pubrec.sourcepackagerelease.version,
                   pubrec.sourcepackagerelease.architecturehintlist))

        for archseries in build_archs:
            # Dismiss if there is no processor available for the
            # archseries in question.
            if not archseries.processors:
                self._logger.debug(
                    "No processors defined for %s: skipping %s"
                    % (archseries.title, header))
                continue
            # Dismiss if build is already present for this
            # distroarchseries.
            if pubrec.sourcepackagerelease.getBuildByArch(
                archseries, pubrec.archive):
                continue
            # Create new Build record.
            self._logger.debug(
                header + "Creating %s (%s)"
                % (archseries.architecturetag, pubrec.pocket.title))
            pubrec.sourcepackagerelease.createBuild(
                distroarchseries=archseries,
                pocket=pubrec.pocket,
                processor=archseries.default_processor,
                archive=pubrec.archive)

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

    def _scoreAndCheckDependencies(self, dependencies_line, archseries):
        """Check dependencies line within a distroarchseries.

        Return tuple containing the designed score points related to
        satisfied/unsatisfied dependencies and a line containing the
        missing dependencies in the default dependency format.
        """
        # parse package build dependencies using apt_pkg
        try:
            parsed_deps = apt_pkg.ParseDepends(dependencies_line)
        except (ValueError, TypeError):
            self._logger.warn("COULD NOT PARSE DEP: %s" % dependencies_line)
            # XXX cprov 2005-10-18:
            # We should remove the job if we could not parse its
            # dependency, but AFAICS, the integrity checks in
            # uploader component will be in charge of this. In
            # short I'm confident this piece of code is never
            # going to be executed
            return 0, dependencies_line

        missing_deps = []
        score = 0

        for token in parsed_deps:
            # XXX cprov 2006-02-27: it may not work for and'd and or'd
            # syntaxes.
            try:
                name, version, relation = token[0]
            except ValueError:
                # XXX cprov 2005-10-18:
                # We should remove the job if we could not parse its
                # dependency, but AFAICS, the integrity checks in
                # uploader component will be in charge of this. In
                # short I'm confident this piece of code is never
                # going to be executed
                self._logger.warn("DEP FORMAT ERROR: '%s'" % token[0])
                return 0, dependencies_line

            dep_candidate = archseries.findDepCandidateByName(name)

            if dep_candidate:
                # use apt_pkg function to compare versions
                # it behaves similar to cmp, i.e. returns negative
                # if first < second, zero if first == second and
                # positive if first > second
                dep_result = apt_pkg.VersionCompare(
                    dep_candidate.binarypackageversion, version)
                # use the previously mapped result to identify whether
                # or not the dependency was satisfied or not
                if version_relation_map[relation](dep_result):
                    # continue for satisfied dependency
                    score -= SCORE_SATISFIEDDEP
                    continue

            # append missing token
            self._logger.warn(
                "MISSING DEP: %r in %s %s"
                % (token, archseries.distroseries.name,
                   archseries.architecturetag))
            missing_deps.append(token)
            score -= SCORE_UNSATISFIEDDEP

        # rebuild dependencies line
        remaining_deps = []
        for token in missing_deps:
            name, version, relation = token[0]
            if relation and version:
                token_str = '%s (%s %s)' % (name, relation, version)
            else:
                token_str = '%s' % name
            remaining_deps.append(token_str)

        return score, ", ".join(remaining_deps)

    def retryDepWaiting(self):
        """Check 'dependency waiting' builds and see if we can retry them.

        Check 'dependencies' field and update its contents. Retry those with
        empty dependencies.
        """
        # Get the missing dependency fields
        arch_ids = [arch.id for arch in self._archserieses]
        status = BuildStatus.MANUALDEPWAIT
        bqset = getUtility(IBuildSet)
        candidates = bqset.getBuildsByArchIds(arch_ids, status=status)
        # XXX cprov 2006-02-27: IBuildSet.getBuildsByArch API is evil,
        # we should always return an SelectResult, even for empty results
        if candidates is None:
            self._logger.debug("No MANUALDEPWAIT record found")
            return

        self._logger.info(
            "Found %d builds in MANUALDEPWAIT state. Checking:"
            % candidates.count())

        for build in candidates:
            # XXX cprov 2006-06-06: This iteration/check should be provided
            # by IBuild.

            if not build.distroseries.canUploadToPocket(build.pocket):
                # skip retries for not allowed in distroseries/pocket
                self._logger.debug('SKIPPED: %s can not build in %s/%s'
                                   % (build.title, build.distroseries.name,
                                      build.pocket.name))
                continue

            if build.dependencies:
                dep_score, remaining_deps = self._scoreAndCheckDependencies(
                    build.dependencies, build.distroarchseries)
                # store new missing dependencies
                build.dependencies = remaining_deps
                if len(build.dependencies):
                    self._logger.debug(
                        'WAITING: %s "%s"' % (build.title, build.dependencies))
                    continue

            # retry build if missing dependencies is empty
            self._logger.debug('RETRY: "%s"' % build.title)
            build.retry()

        self.commit()

    def sanitiseAndScoreCandidates(self):
        """Iter over the buildqueue entries sanitising it."""
        # Get the current build job candidates
        bqset = getUtility(IBuildQueueSet)
        candidates = bqset.calculateCandidates(
            self._archserieses, state=BuildStatus.NEEDSBUILD)
        if not candidates:
            return

        self._logger.info("Found %d build in NEEDSBUILD state. Rescoring"
                          % candidates.count())

        # 1. Remove any for which there are no files (shouldn't happen but
        # worth checking for)
        jobs = []
        for job in candidates:
            if job.files:
                jobs.append(job)
                job.score()
            else:
                distro = job.archseries.distroseries.distribution
                distroseries = job.archseries.distroseries
                archtag = job.archseries.architecturetag
                # remove this entry from the database.
                job.destroySelf()
                self._logger.debug("Eliminating build of %s/%s/%s/%s/%s due "
                                   "to lack of source files"
                                   % (distro.name, distroseries.name,
                                      archtag, job.name, job.version))
            # commit every cycle to ensure it won't be lost.
            self.commit()

        self._logger.info("After paring out any builds for which we "
                           "lack source, %d NEEDSBUILD" % len(jobs))

        # And finally return that list
        return jobs

    def sortByScore(self, queueItems):
        """Sort queueItems by lastscore, in descending order."""
        queueItems.sort(key=operator.attrgetter('lastscore'), reverse=True)

    def sortAndSplitByProcessor(self):
        """Split out each build by the processor it is to be built for then
        order each sublist by its score. Get the current build job candidates
        """
        bqset = getUtility(IBuildQueueSet)
        candidates = bqset.calculateCandidates(
            self._archserieses, state=BuildStatus.NEEDSBUILD)
        if not candidates:
            return {}

        self._logger.debug("Found %d NEEDSBUILD" % candidates.count())

        result = {}

        for job in candidates:
            job_proc = job.archseries.processorfamily
            result.setdefault(job_proc, []).append(job)

        for job_proc in result:
            self.sortByScore(result[job_proc])

        return result

    def dispatchByProcessor(self, proc, queueItems):
        """Dispatch Jobs according specific processor"""
        self._logger.info("dispatchByProcessor(%s, %d queueItem(s))"
                          % (proc.name, len(queueItems)))
        try:
            builders = notes[proc]["builders"]
        except KeyError:
            self._logger.debug("No initialised builders found.")
            return

        while len(queueItems) > 0:
            build_candidate = queueItems.pop(0)
            #self._logger.debug(build_candidate.build.title)
            # Retrieve the first available builder according the context.
            builder = builders.firstAvailable(
                is_trusted=build_candidate.is_trusted)
            if not builder:
                #self._logger.debug('No Builder Available')
                continue
            # either dispatch or mark obsolete builds (sources superseded
            # or removed) as SUPERSEDED.
            spr = build_candidate.build.sourcepackagerelease
            if (spr.publishings and spr.publishings[0].status <=
                dbschema.PackagePublishingStatus.PUBLISHED):
                self.startBuild(builders, builder, build_candidate)
                self.commit()
            else:
                self._logger.debug(
                    "Build %s SUPERSEDED, queue item %s REMOVED"
                    % (build_candidate.build.id, build_candidate.id))
                build_candidate.build.buildstate = (
                    BuildStatus.SUPERSEDED)
                build_candidate.destroySelf()

        self.commit()

    def startBuild(self, builders, builder, queueItem):
        """Find the list of files and give them to the builder."""
        try:
            builder.startBuild(queueItem,  self._logger)
        except BuildSlaveFailure:
            # keep old mirrored-from-db-data in sync.
            builders.updateOkSlaves()
        except CannotBuild:
            # Ignore the exception - this code is being refactored and the
            # caller of startBuild expects it to never fail.
            pass

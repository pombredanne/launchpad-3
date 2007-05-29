#Copyright Canonical Limited 2005-2004
#Authors: Daniel Silverstone <daniel.silverstone@canonical.com>
#         Celso Providelo <celso.providelo@canonical.com>

"""Common code for Buildd scripts

Module used by buildd-queue-builder.py and buildd-slave-scanner.py
cronscripts.
"""

__metaclass__ = type

import operator
import logging
import xmlrpclib
import socket
import datetime
import pytz
import apt_pkg

from zope.component import getUtility

from canonical.librarian.interfaces import ILibrarianClient

from canonical.launchpad.interfaces import (
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


def determineArchitecturesToBuild(pubrec, legal_archreleases,
                                  distrorelease, pas_verify=None):
    """Return a list of DistroArchReleases for which this publication
    should build.

    This function answers the question: given a publication, what
    architectures should we build it for? It takes a set of legal
    distroarchreleases and the distribution release for which we are
    buiilding, and optionally a BuildDaemonPackagesArchSpecific
    instance.
    """
    hint_string = pubrec.sourcepackagerelease.architecturehintlist
    assert hint_string

    legal_arch_tags = set(arch.architecturetag 
                          for arch in legal_archreleases)

    if hint_string == 'any':
        package_tags = legal_arch_tags
    elif hint_string == 'all':
        nominated_arch = distrorelease.nominatedarchindep
        assert nominated_arch in legal_archreleases
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

    sorted_archreleases = sorted(legal_archreleases,
                                 key=operator.attrgetter('architecturetag'))
    return [arch for arch in sorted_archreleases
            if arch.architecturetag in build_tags]


class BuilddMaster:
    """Canonical autobuilder master, toolkit and algorithms.

    Attempt to '_archreleases'  attribute, a dictionary which contains a
    chain of verified DistroArchReleases (by addDistroArchRelease) followed
    by another dictionary containing the available builder-slaver for this
    DistroArchRelease, like :

    # associate  specific processor family to a group of available
    # builder-slaves
    notes[archrelease.processorfamily]['builders'] = builderGroup

    # just to consolidate we have a collapsed information
    buildersByProcessor = notes[archrelease.processorfamily]['builders']

    # associate the extended builderGroup reference to a given
    # DistroArchRelease
    self._archreleases[DAR]['builders'] = buildersByProcessor
    """
    def __init__(self, logger, tm):
        self._logger = logger
        self._tm = tm
        self.librarian = getUtility(ILibrarianClient)
        self._archreleases = {}
        # apt_pkg requires InitSystem to get VersionCompare working properly
        apt_pkg.InitSystem()
        self._logger.info("Buildd Master has been initialised")

    def commit(self):
        self._tm.commit()

    def addDistroArchRelease(self, distroarchrelease):
        """Setting up a workable DistroArchRelease for this session."""
        self._logger.info("Adding DistroArchRelease %s/%s/%s"
                          % (distroarchrelease.distrorelease.distribution.name,
                             distroarchrelease.distrorelease.name,
                             distroarchrelease.architecturetag))

        # check ARCHRELEASE across available pockets
        for pocket in dbschema.PackagePublishingPocket.items:
            if distroarchrelease.getChroot(pocket):
                # Fill out the contents
                self._archreleases.setdefault(distroarchrelease, {})

    def setupBuilders(self, archrelease):
        """Setting up a group of builder slaves for a given DistroArchRelease.

        Use the annotation utility to store a BuilderGroup instance
        keyed by the the DistroArchRelease.processorfamily in the
        global registry 'notes' and refer to this 'note' in the private
        attribute '_archrelease' keyed by the given DistroArchRelease
        and the label 'builders'. This complicated arrangement enables us
        to share builder slaves between different DistroArchRelases since
        their processorfamily values are the same (compatible processors).
        """
        # Determine the builders for this distroarchrelease...
        if archrelease not in self._archreleases:
            # Avoid entering in the huge loop if we don't find at least
            # one architecture for which we can build on.
            self._logger.debug(
                "Chroot missing for %s/%s/%s, skipping"
                % (archrelease.distrorelease.distribution.name,
                   archrelease.distrorelease.name,
                   archrelease.architecturetag))
            return

        builders = self._archreleases[archrelease].get("builders")

        # if annotation for builders was already done, return
        if builders:
            return

        # query the global annotation registry and verify if
        # we have already done the builder checks for the
        # processor family in question. if it's already done
        # simply refer to that information in the _archreleases
        # attribute.
        if 'builders' not in notes[archrelease.processorfamily]:

            # setup a BuilderGroup object
            info = "builders.%s" % archrelease.processorfamily.name
            builderGroup = BuilderGroup(self.getLogger(info), self._tm)

            # check the available slaves for this archrelease
            builderGroup.checkAvailableSlaves(archrelease)

            # annotate the group of builders for the
            # DistroArchRelease.processorfamily in question and the
            # label 'builders'
            notes[archrelease.processorfamily]["builders"] = builderGroup

        # consolidate the annotation for the architecture release
        # in the private attribute _archreleases
        builders = notes[archrelease.processorfamily]["builders"]
        self._archreleases[archrelease]["builders"] = builders

    def createMissingBuilds(self, distrorelease):
        """Ensure that each published package is completly built."""
        self._logger.debug("Processing %s" % distrorelease.name)
        # Do not create builds for distroreleases with no nominatedarchindep
        # they can't build architecture independent packages properly.
        if not distrorelease.nominatedarchindep:
            self._logger.debug(
                "No nominatedarchindep for %s, skipping" % distrorelease.name)
            return

        # listify to avoid hitting this MultipleJoin multiple times
        distrorelease_architectures = list(distrorelease.architectures)
        if not distrorelease_architectures:
            self._logger.debug(
                "No architectures defined for %s, skipping"
                % distrorelease.name)
            return

        registered_arch_ids = set(dar.id for dar in self._archreleases.keys())
        release_arch_ids = set(dar.id for dar in distrorelease_architectures)
        legal_arch_ids = release_arch_ids.intersection(registered_arch_ids)
        legal_archs = [dar for dar in distrorelease_architectures
                       if dar.id in legal_arch_ids]
        if not legal_archs:
            self._logger.debug(
                "Chroots missing for %s, skipping" % distrorelease.name)
            return

        legal_arch_tags = " ".join(a.architecturetag for a in legal_archs)
        self._logger.info("Supported architectures: %s" % legal_arch_tags)

        pas_verify = BuildDaemonPackagesArchSpecific(
            config.builddmaster.root, distrorelease)

        sources_published = distrorelease.getSourcesPublishedForAllArchives()
        self._logger.info(
            "Found %d source(s) published." % sources_published.count())

        # XXX cprov 20050831: Entering this loop with no supported
        # architecture results in a corruption of the persistent DBNotes
        # instance for self._archreleases, it ends up empty. Bug 2070.
        # XXX: I have no idea what celso is talking about above. -- kiko
        for pubrec in sources_published:
            build_archs = determineArchitecturesToBuild(
                            pubrec, legal_archs, distrorelease, pas_verify)
            self._createMissingBuildsForPublication(pubrec, build_archs)

        self.commit()

    def _createMissingBuildsForPublication(self, pubrec, build_archs):
        header = ("build record %s-%s for '%s' " %
                  (pubrec.sourcepackagerelease.name,
                   pubrec.sourcepackagerelease.version,
                   pubrec.sourcepackagerelease.architecturehintlist))
        assert pubrec.sourcepackagerelease.architecturehintlist
        for archrelease in build_archs:
            if not archrelease.processors:
                self._logger.debug(
                    "No processors defined for %s: skipping %s"
                    % (archrelease.title, header))
                return
            if pubrec.sourcepackagerelease.getBuildByArch(
                archrelease, pubrec.archive):
                # verify this build isn't already present for this
                # distroarchrelease
                continue

            self._logger.debug(
                header + "Creating %s (%s)"
                % (archrelease.architecturetag, pubrec.pocket.title))

            pubrec.sourcepackagerelease.createBuild(
                distroarchrelease=archrelease,
                pocket=pubrec.pocket,
                processor=archrelease.default_processor,
                archive=pubrec.archive)


    def addMissingBuildQueueEntries(self):
        """Create missing Buildd Jobs. """
        self._logger.info("Scanning for build queue entries that are missing")

        buildset = getUtility(IBuildSet)
        builds = buildset.getPendingBuildsForArchSet(self._archreleases)

        if not builds:
            return

        for build in builds:
            if not build.buildqueue_record:
                name = build.sourcepackagerelease.name
                version = build.sourcepackagerelease.version
                tag = build.distroarchrelease.architecturetag
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
            proc = job.archrelease.processorfamily
            try:
                builders = notes[proc]["builders"]
            except KeyError:
                continue
            builders.updateBuild(job, self.librarian)

    def getLogger(self, subname=None):
        """Return the logger instance with specific prefix"""
        if subname is None:
            return self._logger
        return logging.getLogger("%s.%s" % (self._logger.name, subname))

    def scoreBuildQueueEntry(self, job, now=None):
        """Score Build Job according several fields

        Generate a Score index according some job properties:
        * distribution release component
        * sourcepackagerelease urgency
        """
        if now is None:
            now = datetime.datetime.now(pytz.timezone('UTC'))

        if job.manual:
            self._logger.debug("%s (%d) MANUALLY RESCORED"
                               % (job.name, job.lastscore))
            return

        score = 0
        score_componentname = {
            'multiverse': 0,
            'universe': 250,
            'restricted': 750,
            'main': 1000,
            }

        score_urgency = {
            dbschema.SourcePackageUrgency.LOW: 5,
            dbschema.SourcePackageUrgency.MEDIUM: 10,
            dbschema.SourcePackageUrgency.HIGH: 15,
            dbschema.SourcePackageUrgency.EMERGENCY: 20,
            }

        # Define a table we'll use to calculate the score based on the time
        # in the build queue.  The table is a sorted list of (upper time
        # limit in seconds, score) tuples.
        queue_time_scores = [
            (14400, 100),
            (7200, 50),
            (3600, 20),
            (1800, 15),
            (900, 10),
            (300, 5),
        ]

        score = 0
        msg = "%s (%d) -> " % (job.build.title, job.lastscore)

        # Calculate the urgency-related part of the score
        score += score_urgency[job.urgency]
        msg += "U+%d " % score_urgency[job.urgency]

        # Calculate the component-related part of the score
        score += score_componentname[job.component_name]
        msg += "C+%d " % score_componentname[job.component_name]

        # Calculate the build queue time component of the score
        eta = now - job.created
        for limit, dep_score in queue_time_scores:
            if eta.seconds > limit:
                score += dep_score
                msg += "%d " % score
                break

        # Score the package down if it has unsatisfiable build-depends
        # in the hope that doing so will allow the depended on package
        # to be built first.
        if job.builddependsindep:
            depindep_score, missing_deps = self._scoreAndCheckDependencies(
                job.builddependsindep, job.archrelease)
            # sum dependency score
            score += depindep_score

        # store current score value
        job.lastscore = score
        self._logger.debug(msg + " = %d" % job.lastscore)

    def _scoreAndCheckDependencies(self, dependencies_line, archrelease):
        """Check dependencies line within a distroarchrelease.

        Return tuple containing the designed score points related to
        satisfied/unsatisfied dependencies and a line containing the
        missing dependencies in the default dependency format.
        """
        # parse package build dependencies using apt_pkg
        try:
            parsed_deps = apt_pkg.ParseDepends(dependencies_line)
        except (ValueError, TypeError):
            self._logger.warn("COULD NOT PARSE DEP: %s" % dependencies_line)
            # XXX cprov 20051018:
            # We should remove the job if we could not parse its
            # dependency, but AFAICS, the integrity checks in
            # uploader component will be in charge of this. In
            # short I'm confident this piece of code is never
            # going to be executed
            return 0, dependencies_line

        missing_deps = []
        score = 0

        for token in parsed_deps:
            # XXX cprov 20060227: it may not work for and'd and or'd
            # syntaxes.
            try:
                name, version, relation = token[0]
            except ValueError:
                # XXX cprov 20051018:
                # We should remove the job if we could not parse its
                # dependency, but AFAICS, the integrity checks in
                # uploader component will be in charge of this. In
                # short I'm confident this piece of code is never
                # going to be executed
                self._logger.warn("DEP FORMAT ERROR: '%s'" % token[0])
                return 0, dependencies_line

            dep_candidate = archrelease.findDepCandidateByName(name)

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
                % (token, archrelease.distrorelease.name,
                   archrelease.architecturetag))
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
        arch_ids = [arch.id for arch in self._archreleases]
        status = dbschema.BuildStatus.MANUALDEPWAIT
        bqset = getUtility(IBuildSet)
        candidates = bqset.getBuildsByArchIds(arch_ids, status=status)
        # XXX cprov 20060227: IBuildSet.getBuildsByArch API is evil,
        # we should always return an SelectResult, even for empty results
        if candidates is None:
            self._logger.debug("No MANUALDEPWAIT record found")
            return

        self._logger.info(
            "Found %d builds in MANUALDEPWAIT state. Checking:"
            % candidates.count())

        for build in candidates:
            # XXX cprov 20060606: This iteration/check should be provided
            # by IBuild.

            if not build.distrorelease.canUploadToPocket(build.pocket):
                # skip retries for not allowed in distrorelease/pocket
                self._logger.debug('SKIPPED: %s can not build in %s/%s'
                                   % (build.title, build.distrorelease.name,
                                      build.pocket.name))
                continue

            if build.dependencies:
                dep_score, remaining_deps = self._scoreAndCheckDependencies(
                    build.dependencies, build.distroarchrelease)
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
            self._archreleases, state=dbschema.BuildStatus.NEEDSBUILD)
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
                self.scoreBuildQueueEntry(job)
            else:
                distro = job.archrelease.distrorelease.distribution
                distrorelease = job.archrelease.distrorelease
                archtag = job.archrelease.architecturetag
                # remove this entry from the database.
                job.destroySelf()
                self._logger.debug("Eliminating build of %s/%s/%s/%s/%s due "
                                   "to lack of source files"
                                   % (distro.name, distrorelease.name,
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
            self._archreleases, state=dbschema.BuildStatus.NEEDSBUILD)
        if not candidates:
            return {}

        self._logger.debug("Found %d NEEDSBUILD" % candidates.count())

        result = {}

        for job in candidates:
            job_proc = job.archrelease.processorfamily
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
            else:
                self._logger.debug(
                    "Build %s SUPERSEDED, queue item %s REMOVED"
                    % (build_candidate.build.id, build_candidate.id))
                build_candidate.build.buildstate = (
                    dbschema.BuildStatus.SUPERSEDED)
                build_candidate.destroySelf()

        self.commit()

    def startBuild(self, builders, builder, queueItem):
        """Find the list of files and give them to the builder."""
        pocket = queueItem.build.pocket

        self._logger.info("startBuild(%s, %s, %s, %s)"
                           % (builder.url, queueItem.name,
                              queueItem.version, pocket.title))

        # ensure build has the need chroot
        chroot = queueItem.archrelease.getChroot(pocket)
        if chroot is None:
            self._logger.debug(
                "Missing CHROOT for %s/%s/%s/%s"
                % (queueItem.build.distrorelease.distribution.name,
                   queueItem.build.distrorelease.name,
                   queueItem.build.distroarchrelease.architecturetag,
                   queueItem.build.pocket.name))
            return

        try:
            # Resume build XEN-images
            builders.resumeBuilder(builder)
            # Send chroot.
            builders.giveToBuilder(builder, chroot, self.librarian)

            # Build filemap structure with the files required in this build
            # and send them to the builder.
            filemap = {}
            for f in queueItem.files:
                fname = f.libraryfile.filename
                filemap[fname] = f.libraryfile.content.sha1
                builders.giveToBuilder(builder, f.libraryfile, self.librarian)

            # Build extra arguments
            args = {}
            args["ogrecomponent"] = queueItem.component_name
            # turn 'arch_indep' ON only if build is archindep or if
            # the specific architecture is the nominatedarchindep for
            # this distrorelease (in case it requires any archindep source)
            # XXX: there is no point in checking if archhintlist ==
            # 'all' here, because it's redundant with the check for
            # isNominatedArchIndep. -- kiko, 2006-08-31
            args['arch_indep'] = (queueItem.archhintlist == 'all' or
                                  queueItem.archrelease.isNominatedArchIndep)
            # XXX cprov 20070523: Ogre should not be modelled here ...
            if not queueItem.is_trusted:
                ogre_map = {
                    'main': 'main',
                    'restricted': 'main restricted',
                    'universe': 'main restricted universe',
                    'multiverse': 'main restricted universe multiverse',
                    }
                ogre_components = ogre_map[queueItem.component_name]
                # XXX cprov 20070523: it should be suite name, but it
                # is just fine for PPAs since they are only built in
                # RELEASE pocket.
                dist_name = queueItem.archrelease.distrorelease.name
                ppa_archive_url = queueItem.build.archive.archive_url
                ppa_source_line = (
                    'deb %s/ubuntu %s %s'
                    % (ppa_archive_url, dist_name, ogre_components))
                ubuntu_source_line = (
                    'deb http://archive.ubuntu.com/ubuntu %s %s'
                    % (dist_name, ogre_components))
                args['archives'] = [ppa_source_line, ubuntu_source_line]
            else:
                args['archives'] = []

            # Request start of the process.
            builders.startBuild(
                builder, queueItem, filemap, "debian", pocket, args)

        except (xmlrpclib.Fault, socket.error), info:
            # mark builder as 'failed'.
            self._logger.debug(
                "Disabling builder: %s" % builder.url, exc_info=1)
            builders.failBuilder(
                builder, "Exception (%s) when setting up to new job" % info)

        self.commit()


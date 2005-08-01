#Copyright Canonical Limited 2005-2004
#Authors: Daniel Silverstone <daniel.silverstone@canonical.com>
#         Celso Providelo <celso.providelo@canonical.com>

""" Common code for Buildd scripts and daemons such as queuebuilder.py
and slave-scanner-daemon.py.
"""

__metaclass__ = type

__all__ = ['BuilddMaster']

# XXX 20050617 cprov
# needs total refactoring for using common zcml configuration
# execute_zcml_for_script() then getUtility() and so on. 


import logging
import warnings
import xmlrpclib
import os
import socket
from cStringIO import StringIO

from sqlobject.sqlbuilder import AND, IN

from canonical.launchpad.database import (
    Builder, BuildQueue, Build, Distribution, DistroRelease,
    DistroArchRelease, SourcePackagePublishing, LibraryFileAlias,
    BinaryPackage, BinaryPackageFile, BinaryPackageName,
    SourcePackageReleaseFile
    )

from canonical.lp.dbschema import (
    PackagePublishingStatus, PackagePublishingPocket, 
    BinaryPackageFormat, BinaryPackageFileType
    )

from canonical.lp.dbschema import BuildStatus as DBBuildStatus

from canonical.librarian.client import LibrarianClient

from canonical.database.constants import nowUTC

from canonical.launchpad.helpers import filenameToContentType

from canonical.buildd.slave import BuilderStatus, BuildStatus
from canonical.buildd.utils import notes


# XXX cprov 20050628
# I couldn't found something similar in hct.utils, but probably there is.
# as soon as I can get a brief talk with Scott, this code must be removed.
def extractNameAndVersion(filename):
    """ Extract name and version from the filename.
    
    >>> extractNameAndVersion('at_3.1.8-11ubuntu2_i386.deb')
    ('at', '3.1.8-11ubuntu2')

    """
    name, version, ignored = filename.split("_", 3)[:3]
    return name, version

class BuildDaemonError(Exception):
    """The class of errors raised by the buildd classes"""


class BuilderGroup:
    """Manage a set of builders based on a given architecture"""

    def commit(self):
        self._tm.commit()

    def rollback(self):
        self._tm.rollback()

    def __init__(self, logger, tm):
        self._tm = tm
        self.logger = logger

    def checkAvailableSlaves(self, archFamilyId, archTag):
        """Iter through available builder-slaves for an given architecture."""
        # available slaves
        self.builders = Builder.select('builder.processor = processor.id '
                                       'AND processor.family = %d'
                                       % archFamilyId,
                                       clauseTables=("Processor",))
        # Actualise the results because otherwise we get our exceptions
        # at odd times
        self.logger.debug("Initialising builders for " + archTag)

        self.builders = set(self.builders)

        self.logger.debug("Finding XMLRPC clients for the builders")

        for builder in self.builders:
            # verify if the builder has been disabled
            if not builder.builderok:
                continue
            try:
                # verify the echo method
                if builder.slave.echo("Test")[0] != "Test":
                    raise ValueError, "Failed to echo OK"

                # ask builder information
                vers, methods, arch, mechanisms = builder.slave.info()

                # attempt to wrong builder version 
                if vers != 1:
                    raise ValueError, "Protocol version mismatch"

                # attempt to wrong builder architecture
                if arch != archTag:
                    raise ValueError, ("Architecture tag mismatch: %s != %s"
                                       % (arch, archTag))
            # attemp only to known exceptions 
            except (ValueError, TypeError, xmlrpclib.Fault,
                    socket.error), reason:
                builder.builderok = False
                builder.failnote = reason
                self.logger.debug("Builder on %s marked as failed due to: %s",
                                  builder.url, reason, exc_info=True)


        self.updateOkSlaves()


    def updateOkSlaves(self):
        self.okslaves = [b for b in self.builders if b.builderok]
        if len(self.okslaves) == 0:
            self.logger.debug("They're all dead. Everybody's dead, Dave.")
            self.logger.warn("No builders are available")

    def failBuilder(self, builder, reason):
        builder.builderok = False
        builder.failnote = reason
        self.updateOkSlaves()

    def giveToBuilder(self, builder, libraryfilealias, librarian):
        if not builder.builderok:
            raise BuildDaemonError("Attempted to give a file to a known-bad"
                                   " builder")

        url = librarian.getURLForAlias(libraryfilealias.id)
        
        self.logger.debug("Asking builder on %s if it has file %s (%s, %s)"
                          % (builder.url, libraryfilealias.filename,
                             url, libraryfilealias.content.sha1))
        
        if not builder.slave.doyouhave(libraryfilealias.content.sha1, url):
            warnings.warn('oops: Deprecated method, Verify if Slave can '
                          'properly access librarian',
                          DeprecationWarning)

            self.logger.debug("Attempting to fetch %s to give to builder on %s"
                              % (libraryfilealias.content.sha1, builder.url))
            # 1. Get the file download object going
            # XXX cprov 20050628
            # It fails because the URL gets unescaped?
            download = librarian.getFileByAlias(libraryfilealias.id)
            file_content = xmlrpclib.Binary(download.read())
            download.close()
            # 2. Give the file to the remote end.
            self.logger.debug("Passing it on...")
            storedsum = builder.slave.storefile(file_content)
            if storedsum != libraryfilealias.content.sha1:
                raise BuildDaemonError, ("Storing to buildd slave failed, "
                                         "%s != %s"
                                         % (storedsum,
                                            libraryfilealias.content.sha1))
        else:
            self.logger.debug("It does")

    def findChrootFor(self, buildCandidate, pocket):
        """Return the CHROOT digest for an pair (buildCandidate, pocket).
        With the digest in hand we can point the slave to grab it himself.
        Return None if it wasn't found.
        """
        archrelease = buildCandidate.build.distroarchrelease
        chroot = archrelease.getChroot(pocket)
        if chroot:
            return chroot.content.sha1        

    def startBuild(self, builder, queueItem, filemap, buildtype, pocket):
        buildid = "%s-%s" % (queueItem.build.id, queueItem.id)
        self.logger.debug("Initiating build %s on %s"
                          % (buildid, builder.url))
        queueItem.builder = builder
        queueItem.buildstart = nowUTC
        chroot = self.findChrootFor(queueItem, pocket)
        if not chroot:
            self.logger.debug("OOPS! Could not find CHROOT")
            return
        
        builder.slave.startbuild(buildid, filemap, chroot, buildtype)

    def getLogFromSlave(self, slave, buildid, librarian):
        log = slave.fetchlogtail()
        slog = str(log)
        sio = StringIO(slog)
        aliasid = librarian.addFile("log-for-%s" % buildid,
                                    len(slog), sio,
                                    contentType="text/plain");
        # XXX: dsilvers: 20050302: Remove these when the library works
        self.commit()
        return aliasid

    def getFileFromSlave(self, slave, filename, sha1sum, librarian):
        """Request a file from Slave by passing a digest and store it in
        Librarian  with correspondent filename.
        """
        # XXX cprov 20050701
        # What if the file wasn't available on Slave ?
        # The chance of it happens are too low, since Master just requests
        # files (digests) sent by Slave. but we should be aware of this
        # possibilty.

        # receive an xmlrpc.Binary object containg the correspondent file
        # for a given digest
        filedata = slave.fetchfile(sha1sum)
        # transform the data in a file object, because librarian requires it
        # and attempt we need to cast the xmlrpc.Bynary object to a string
        fileobj = StringIO(str(filedata))
        # figure out the MIME content-type
        ftype = filenameToContentType(filename)
        
        aliasid = librarian.addFile(filename, len(str(filedata)), fileobj,
                                    contentType=ftype)

        # XXX: dsilvers: 20050302: Remove these when the library works
        self.commit()
        return aliasid

    def processBinaryPackage(self, build, aliasid, filename):
        alias = LibraryFileAlias.get(aliasid)
        binname, version = extractNameAndVersion(filename)

        archdep = not filename.endswith("all.deb")

        binnameid = BinaryPackageName.ensure(binname)

        # XXX cprov 20050628
        # Try to use BinaryPackageSet utility for this job 
        binpkgid = BinaryPackage(binarypackagename=binnameid,
                                 version=version,
                                 build=build,
                                 binpackageformat=BinaryPackageFormat.DEB,
                                 architecturespecific=archdep,
                                 # storing  binary entry inside main component
                                 # and section
                                 component=1, 
                                 section=1, 
                                 # XXX cprov 20050628
                                 # Those fields should be extracted form the
                                 # dsc file somehow, maybe apt_pkg ? 
                                 summary="",
                                 description="",
                                 priority=None,
                                 shlibdeps=None,
                                 depends=None,
                                 recommends=None,
                                 suggests=None,
                                 conflicts=None,
                                 replaces=None,
                                 provides=None,
                                 essential=None,
                                 installedsize=None,
                                 copyright=None,
                                 licence=None)
        
        binfile = BinaryPackageFile(binarypackage=binpkgid,
                                    libraryfile=alias,
                                    filetype=BinaryPackageFileType.DEB)
        
        self.logger.debug("Absorbed binary package %s" % filename)
        
    def updateBuild(self, queueItem, librarian):
        """Verify the current build job status and perform the required
        actions for each state.
        """
        # build the slave build job id key
        buildid = "%s-%s" % (queueItem.build.id, queueItem.id)

        # retrieve slave xmlrpc instance correspondent to this build
        slave = queueItem.builder.slave

        try:
            res = slave.status()
        except xmlrpclib.Fault, info:
            # XXX cprov 20050629
            # Hmm, a problem with the xmlrpc interface,
            # disable the builder ?? or simple notice the failure
            # with a timesamp.
            info = ("Could not contact the builder %s, caught a (%s)"
                    % (queueItem.builder.url, info))
            self.logger.debug(info, exc_info=True)
            # keep the job for scan
            return

        # res = ('<status>', ..., ...)
        status = res[0]

        assert status.startswith('BuilderStatus.')

        status = status[len('BuilderStatus.'):]
        method = getattr(self, 'updateBuild_' + status, None)

        if method is None:
            self.logger.critical("Builder on %s returned unknown status %s,"
                                 " failing it" % (queueItem.builder.url,
                                                  status))
            self.failBuilder(queueItem.builder,
                             ("Unknown status code (%s) returned from "
                              "status() probe." % status))
            queueItem.builder = None
            queueItem.buildstart = None  
            
        try:
            method(queueItem, slave, librarian, *res[1:])
        except TypeError:
            self.logger.critical("Received wrong number of args in response.")

        self.commit()

    def updateBuild_IDLE(self, queueItem, slave, librarian):
        """Somehow the builder forgot about the build log this and reset
        the record.
        """
        release = queueItem.build.sourcepackagerelease
        self.logger.warn("Builder on %s is Dory AICMFP. "
                         "Builder forgot about build %s of %s (%s) "
                         "-- resetting buildqueue record"
                         % (queueItem.builder.url, buildid,
                            release.sourcepackagename.name,
                            release.version))            
        
        queueItem.builder = None
        queueItem.buildstart = None

    def updateBuild_BUILDING(self, queueItem, slave, librarian, buildid,
                             logtail):
        """Build still building, Simple collects the logtail"""
        # XXX: dsilvers: 20050302: Confirm the builder has the right build?
        queueItem.logtail = logtail

    def updateBuild_WAITING(self, queueItem, slave, librarian, buildstatus,
                            buildid, filemap=None):
        """Build can be WAITING in two situations:

        * Build has failed, no filemap is received
        
        * Build has been built successfully (BuildStatus.OK), in this case
          we have a 'filemap', so we can retrive those files and store in
          Librarian with getFileFromSlave() and install the binary in LP
          with processBinary() (the last should change when we have publisher
          component available).
        """
        # XXX: dsilvers: 20050302: Confirm the builder has the right build?
        queueItem.build.buildlog = self.getLogFromSlave(slave, buildid,
                                                        librarian)
        queueItem.build.datebuilt = nowUTC

        if buildstatus == BuildStatus.OK:
            # Builder has built package entirely, get all the content back
            queueItem.build.builder = queueItem.builder

            #XXX: dsilvers: 20050302: How do I get an interval for here?
            #queueItem.build.buildduration = queueItem.buildstart
            queueItem.build.buildstate = DBBuildStatus.FULLYBUILT

            for result in filemap:
                aliasid = self.getFileFromSlave(slave, result, filemap[result],
                                                librarian)
                if result.endswith(".deb"):
                    # Process a binary package
                    self.processBinaryPackage(queueItem.build, aliasid, result)
                    release = queueItem.build.sourcepackagerelease
                    self.logger.debug("Gathered build of %s completely"
                                      % release.sourcepackagename.name)
            # release the builder and remove BQ entry
            slave.clean()
            queueItem.destroySelf()

    def updateBuild_DEPFAIL(self, queueItem, slave, librarian, info):
        """Build has failed by missing dependencies, set the job status as
        MANUALDEPWAIT, requires human interaction to free the builder slave.
        """
        queueItem.build.buildstate = DBBuildStatus.MANUALDEPWAIT

    def updateBuild_PACKAGEFAIL(self, queueItem, slave, librarian, info):
        """Build has failed when trying the work with the target package,
        set the job status as FAILEDTOBUILD and also requires human
        interaction to free the builder slave.
        """
        queueItem.build.buildstate = DBBuildStatus.FAILEDTOBUILD

    def updateBuild_CHROOTFAIL(self, queueItem, slave, librarian, info):
        """Build has failed when installing the current CHROOT, mark the
        job as CHROOTFAIL and leave builder slave blocked.
        """
        queueItem.build.buildstate = DBBuildStatus.CHROOTWAIT

    def updateBuild_BUILDERFAIL(self, queueItem, slave, librarian, info):
        """Build has been failed when trying to build the target package,
        The environment is working well, so mark the job as NEEDSBUILD again
        and 'clean' the builder to do another jobs. 
        """
        queueItem.build.buildstate = DBBuildStatus.NEEDSBUILD
        self.failBuilder(queueItem.builder,
                         ("Builder returned BUILDERFAIL when asked "
                          "for its status"))
        # And reset the builder information
        if queueItem.builder.builderok:
            slave.clean()
        queueItem.builder = None
        queueItem.buildstart = None

    def updateBuild_ABORTED(self, queueItem, slave, librarian, buildid):
        """Build was ABORTED, 'clean' the builder for another jobs. """
        # XXX: dsilvers: 20050302: Confirm the builder has the right build?
        queueItem.builder = None
        queueItem.buildstart = None
        slave.clean()
            
    def countAvailable(self):
        count = 0
        for builder in self.builders:
            if builder.builderok:
                slave = builder.slave
                try:
                    slavestatus = slave.status()
                except Exception, e:
                    self.logger.debug("Builder %s wasn't counted due (%s)."
                                      % (builder.url, e))
                    continue              
                if slavestatus[0] == BuilderStatus.IDLE:
                    count += 1
        return count

    def firstAvailable(self):
        """Return the first available builder slave connection instance or
        None if there is no one.
        """
        for builder in self.builders:
            if builder.builderok:
                slave = builder.slave
                try:
                    slavestatus = slave.status()
                except Exception, e:
                    self.logger.debug("Builder %s wasn't counted due (%s)."
                                      % (builder.url, e))
                    continue
                if slavestatus[0] == BuilderStatus.IDLE:
                    return builder
        return


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
        self.librarian = LibrarianClient()
        self._archreleases = {}
        self._logger.info("Buildd Master has been initialised")
        
    def commit(self):
        self._tm.commit()

    def rollback(self):
        self._tm.rollback()

    def addDistroArchRelease(self, archrelease, pocket=None):        
        """Setting up a workable DistroArchRelease for this session."""
        # ensure we have a pocket
        if not pocket:
            pocket = PackagePublishingPocket.PLAIN

        self._logger.info("Adding DistroArchRelease %s/%s/%s/%s"
                          % (archrelease.distrorelease.distribution.name,
                             archrelease.distrorelease.name,
                             archrelease.architecturetag, pocket))
        # ensure ARCHRELEASE has a pocket
        if not archrelease.getChroot(pocket):
            self._logger.warn("Disabling: No CHROOT found for pocket '%s'"
                              % pocket.title)
            return
        
        # Fill out the contents
        self._archreleases.setdefault(archrelease, {})
    
    def setupBuilders(self, archrelease):
        """Setting up a group of builder slaves for a given DistroArchRelease.
        """
        # Determine the builders for this distroarchrelease...
        builders = self._archreleases[archrelease].get("builders")

        if builders is None:
            if 'builders' not in notes[archrelease.processorfamily]:
                info = "builders.%s" % archrelease.processorfamily.name
                # setup a BuilderGroup object
                builderGroup = BuilderGroup(self.getLogger(info), self._tm)

                # check the available slaves for this archrelease
                archFamilyId = archrelease.processorfamily.id
                archTag = archrelease.architecturetag
                builderGroup.checkAvailableSlaves(archFamilyId, archTag)

                notes[archrelease.processorfamily]["builders"] = builderGroup
                
            builders = notes[archrelease.processorfamily]["builders"]
            self._archreleases[archrelease]["builders"] = builders

                                                         
    def createMissingBuilds(self, distrorelease):
        """Iterate over published package and ensure we have a proper
        build entry for it.
        """
        # 1. get all sourcepackagereleases published or pending in this
        # distrorelease
        pending = PackagePublishingStatus.PENDING.value
        published = PackagePublishingStatus.PUBLISHED.value
        
        spp = SourcePackagePublishing.select('distrorelease=%d AND '
                                             '(status=%d OR status=%d)'
                                             % (distrorelease.id,
                                                pending, published))
        
        self._logger.info("Scanning publishing records for %s/%s...",
                          distrorelease.distribution.name,
                          distrorelease.name)

        releases = set(pubrec.sourcepackagerelease for pubrec in spp)

        self._logger.info("Found %d Sources to build.", len(releases))

        # 2. Determine the set of distroarchreleases we care about in this
        # cycle
        archs = set([arch for arch in distrorelease.architectures
                     if arch in self._archreleases])
        
        # 3. For each of the sourcepackagereleases, find its builds...
        for release in releases:
            for arch in archs:
                builds = Build.selectBy(sourcepackagereleaseID=release.id,
                                        distroarchreleaseID=arch.id)
                if builds.count() == 0:
                    self._logger.debug("Creating build record for %s (%s) "
                                       "on %s"
                                       % (release.sourcepackagename.name,
                                          release.version,
                                          arch.architecturetag))
                    
                    # XXX: dsilvers: 21/2/05: processor?! NULL?
                    # Also, what's with having to pass all these None values ?
                    # cprov 20050701
                    # As soon as I can land the refactoring for using
                    # getUtility() this issue and other can be solved. 
                    Build(processor=1,
                          distroarchrelease=arch.id,
                          buildstate=DBBuildStatus.NEEDSBUILD,
                          sourcepackagerelease=release.id,
                          buildduration=None,
                          gpgsigningkey=None,
                          builder=None,
                          buildlog=None,
                          datebuilt=None,
                          changes=None,
                          datecreated=nowUTC
                          )
        self.commit()

    def addMissingBuildQueueEntries(self):
        """Create missed Buiild Jobs. """
        self._logger.debug("Scanning for build queue entries that are missing")
        # 1. Get all builds in NEEDSBUILD which are for a distroarchrelease
        # that we build...
        # XXX cprov 20050629
        # use sqlbuilder to improve the clarity of the query
        # not reached at all.
        archreleases = [d.id for d in self._archreleases]
        if len(archreleases) == 0:
            archreleases = [0]
            
        builds = Build.select(
            AND(Build.q.buildstate==DBBuildStatus.NEEDSBUILD,
                IN(Build.q.distroarchreleaseID, archreleases))
                )                                  
        
        for build in builds:
            if BuildQueue.selectBy(buildID=build.id).count() == 0:
                name = build.sourcepackagerelease.sourcepackagename.name
                version = build.sourcepackagerelease.version
                tag = build.distroarchrelease.architecturetag
                self._logger.debug("Creating buildqueue record for %s (%s) "
                                   " on %s" % (name, version, tag))
                
                BuildQueue(build=build.id,
                           builder=None,
                           created=nowUTC,
                           buildstart=None,
                           lastscore=None,
                           logtail=None)
        self.commit()


    def scanActiveBuilders(self):
        """Collect informations/results of current build jobs."""
        # Find a list of all BuildQueue items which indicate they're active
        queueItems = BuildQueue.select("BuildQueue.Builder IS NOT NULL")

        self.getLogger().debug("scanActiveBuilders() found %d active "
                               "build(s) to check" % queueItems.count())

        for job in queueItems:
            proc = job.build.distroarchrelease.processorfamily
            try:
                builders = notes[proc]["builders"]
            except KeyError:
                continue
            builders.updateBuild(job, self.librarian)

        self.commit()

    def getLogger(self, subname=None):
        if subname is None:
            return self._logger
        l = logging.getLogger("%s.%s" % (self._logger.name, subname))
        return l

    def calculateCandidates(self):
        """Return the candidates for building as a list of buildqueue items
        which need ordering.
        """
        # 1. determine all buildqueue items which needsbuild
        tries = ["build.distroarchrelease=%d" % d.id for d in
                 self._archreleases]

        clause = " OR ".join(tries)

        if clause == '':
            clause = "false";
        
        candidates = BuildQueue.select("buildqueue.build = build.id AND "
                                       "build.buildstate = %d AND "
                                       "buildqueue.builder IS NULL AND (%s)"
                                       % (DBBuildStatus.NEEDSBUILD.value,
                                          clause),
                                       clauseTables=['Build'])
        
        self._logger.debug("Found %d NEEDSBUILD" % candidates.count())

        return candidates

    def scoreBuildQueueEntries(self, tobuild):
        """Score Build Jobs according several fields"""
        for job in tobuild:
            # For now; each element gets a score of 1 point
            job.lastscore = 1

        self.commit()

    def sanitiseAndScoreCandidates(self):
        """Iter over the buildqueue entries sanitising it."""
        # Get the current build job candidates
        candidates = self.calculateCandidates()

        # 1. Remove any for which there are no files (shouldn't happen but
        # worth checking for)
        jobs = []
        for job in candidates:
            if len(job.build.sourcepackagerelease.files) > 0:
                jobs.append(job)
            else:
                distro = job.build.distroarchrelease.distrorelease.distribution
                distrorelease = job.build.distroarchrelease.distrorelease
                archtag = job.build.distroarchrelease.architecturetag
                srcpkg = job.build.sourcepackagerelease.sourcepackagename
                version = job.build.sourcepackagerelease.version
                # remove this entry from the database.
                job.destroySelf()
                # commit here to ensure it won't be lost.
                self.commit()                
                self._logger.debug("Eliminating build of %s/%s/%s/%s/%s due "
                                   "to lack of source files"
                                   % (distro.name, distrorelease.name,
                                      archtag, srcpkg.name, version))
            
        self._logger.debug("After paring out any builds for which we "
                           "lack source, %d NEEDSBUILD" % len(jobs))

        # 2. Eliminate any which we know we can't build (e.g. for dependency
        # reasons)
        # XXX: dsilvers: 2005-02-22: Implement me?


        # 3 Score candidates
        self.scoreBuildQueueEntries(jobs)

        # And finally return that list        
        return jobs

    def sortByScore(self, queueItems):
        queueItems.sort(key=lambda x: x.lastscore)

    def sortAndSplitByProcessor(self):
        """Split out each build by the processor it is to be built for then
        order each sublist by its score. Get the current build job candidates
        """
        candidates = self.calculateCandidates()

        result = {}

        for job in candidates:
            job_proc = job.build.distroarchrelease.processorfamily
            result.setdefault(job_proc, []).append(job)

        for job_proc in result:
            self.sortByScore(result[job_proc])
            
        return result

    def dispatchByProcessor(self, proc, queueItems, pocket=None):
        """Dispach Jobs according specific procesor and pocket """
        # ensure we have a pocket
        if not pocket:
            pocket = PackagePublishingPocket.PLAIN
        
        self.getLogger().debug("dispatchByProcessor(%s, %d queueItem(s), %s)"
                               % (proc.name, len(queueItems), pocket.title))
        builders = notes[proc]["builders"]
        builder = builders.firstAvailable()

        while builder is not None and len(queueItems) > 0:
            self.startBuild(builders, builder, queueItems.pop(0), pocket)
            builder = builders.firstAvailable()                

    def startBuild(self, builders, builder, queueitem, pocket):
        """Find the list of files and give them to the builder."""
        srcname = queueitem.build.sourcepackagerelease.sourcepackagename.name
        version = queueitem.build.sourcepackagerelease.version
        archrelease = queueitem.build.distroarchrelease
        spr = queueitem.build.sourcepackagerelease
        files = spr.files

        self.getLogger().debug("startBuild(%s, %s, %s, %s)"
                               % (builder.url, srcname,
                                  version, pocket.title))

        # ensure build has the need chroot
        chroot = archrelease.getChroot(pocket)

        try:
            builders.giveToBuilder(builder, chroot, self.librarian)
        except Exception, e:
            self._logger.warn("Disabling builder: %s" % builder.url,
                              exc_info=1)
            builders.failBuilder(builder, ("Exception %s passing a chroot"
                                           "to the builder" % e))
        else:
            filemap = {}
            
            for f in files:
                fname = f.libraryfile.filename
                filemap[fname] = f.libraryfile.content.sha1
                builders.giveToBuilder(builder, f.libraryfile, self.librarian)
                
            builders.startBuild(builder, queueitem, filemap,
                                "debian", pocket)
        self.commit()

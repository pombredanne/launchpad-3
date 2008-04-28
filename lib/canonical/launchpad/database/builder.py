# Copyright 2004-2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = [
    'Builder',
    'BuilderSet',
    ]

import httplib
import gzip
import logging
import os
import socket
import subprocess
import tempfile
import urllib2
import xmlrpclib

from zope.interface import implements
from zope.component import getUtility

from sqlobject import (
    StringCol, ForeignKey, BoolCol, IntCol, SQLObjectNotFound)

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.buildd.slave import BuilderStatus
from canonical.buildmaster.master import BuilddMaster
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.database.buildqueue import BuildQueue
from canonical.launchpad.validators.person import public_person_validator
from canonical.launchpad.helpers import filenameToContentType
from canonical.launchpad.interfaces import (
    ArchivePurpose, BuildDaemonError, BuildSlaveFailure, BuildStatus,
    CannotBuild, CannotResumeHost, IBuildQueueSet, IBuildSet,
    IBuilder, IBuilderSet, IDistroArchSeriesSet, IHasBuildRecords,
    NotFoundError, PackagePublishingPocket, PackagePublishingStatus,
    ProtocolVersionMismatch, pocketsuffix)
from canonical.launchpad.webapp.uri import URI
from canonical.launchpad.webapp import urlappend
from canonical.librarian.interfaces import (
    ILibrarianClient, IRestrictedLibrarianClient)
from canonical.librarian.utils import copy_and_close


class TimeoutHTTPConnection(httplib.HTTPConnection):
    def connect(self):
        """Override the standard connect() methods to set a timeout"""
        ret = httplib.HTTPConnection.connect(self)
        self.sock.settimeout(config.builddmaster.socket_timeout)
        return ret


class TimeoutHTTP(httplib.HTTP):
    _connection_class = TimeoutHTTPConnection


class TimeoutTransport(xmlrpclib.Transport):
    """XMLRPC Transport to setup a socket with defined timeout"""
    def make_connection(self, host):
        host, extra_headers, x509 = self.get_host_info(host)
        return TimeoutHTTP(host)


class BuilderSlave(xmlrpclib.Server):
    """Add in a few useful methods for the XMLRPC slave."""

    def __init__(self, urlbase):
        """Initialise a Server with specific parameter to our buildfarm."""
        self.urlbase = urlbase
        rpc_url = urlappend(urlbase, "rpc")
        xmlrpclib.Server.__init__(self, rpc_url,
                                  transport=TimeoutTransport(),
                                  allow_none=True)

    def getFile(self, sha_sum):
        """Construct a file-like object to return the named file."""
        filelocation = "filecache/%s" % sha_sum
        fileurl = urlappend(self.urlbase, filelocation)
        return urllib2.urlopen(fileurl)


class Builder(SQLBase):

    implements(IBuilder, IHasBuildRecords)
    _table = 'Builder'

    _defaultOrder = ['processor', 'virtualized', 'name']

    processor = ForeignKey(dbName='processor', foreignKey='Processor',
                           notNull=True)
    url = StringCol(dbName='url', notNull=True)
    name = StringCol(dbName='name', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        validator=public_person_validator, notNull=True)
    builderok = BoolCol(dbName='builderok', notNull=True)
    failnotes = StringCol(dbName='failnotes', default=None)
    virtualized = BoolCol(dbName='virtualized', default=False, notNull=True)
    speedindex = IntCol(dbName='speedindex', default=0)
    manual = BoolCol(dbName='manual', default=False)
    vm_host = StringCol(dbName='vm_host', default=None)
    active = BoolCol(dbName='active', default=True)

    def cacheFileOnSlave(self, logger, libraryfilealias, private_file):
        """See IBuilder."""
        if private_file:
            librarian = getUtility(IRestrictedLibrarianClient)
        else:
            librarian = getUtility(ILibrarianClient)
        url = librarian.getURLForAlias(libraryfilealias.id)
        logger.debug("Asking builder on %s to ensure it has file %s "
                     "(%s, %s)" % (self.url, libraryfilealias.filename,
                                   url, libraryfilealias.content.sha1))
        if not self.builderok:
            raise BuildDaemonError("Attempted to give a file to a known-bad"
                                   " builder")
        present, info = self.slave.ensurepresent(
            libraryfilealias.content.sha1, url)
        if not present:
            message = """Slave '%s' (%s) was unable to fetch file.
            ****** URL ********
            %s
            ****** INFO *******
            %s
            *******************
            """ % (self.name, self.url, url, info)
            raise BuildDaemonError(message)

    def checkCanBuildForDistroArchSeries(self, distro_arch_series):
        """See IBuilder."""
        # XXX cprov 2007-06-15:
        # This function currently depends on the operating system specific
        # details of the build slave to return a processor-family-name (the
        # architecturetag) which matches the distro_arch_series. In reality,
        # we should be checking the processor itself (e.g. amd64) as that is
        # what the distro policy is set from, the architecture tag is both
        # distro specific and potentially different for radically different
        # distributions - its not the right thing to be comparing.

        # query the slave for its active details.
        # XXX cprov 2007-06-15: Why is 'mechanisms' ignored?
        builder_vers, builder_arch, mechanisms = self.slave.info()
        # we can only understand one version of slave today:
        if builder_vers != '1.0':
            raise ProtocolVersionMismatch("Protocol version mismatch")
        # check the slave arch-tag against the distro_arch_series.
        if builder_arch != distro_arch_series.architecturetag:
            raise BuildDaemonError(
                "Architecture tag mismatch: %s != %s"
                % (builder_arch, distro_arch_series.architecturetag))

    def checkSlaveAlive(self):
        """See IBuilder."""
        if self.slave.echo("Test")[0] != "Test":
            raise BuildDaemonError("Failed to echo OK")

    def cleanSlave(self):
        """See IBuilder."""
        return self.slave.clean()

    @property
    def currentjob(self):
        """See IBuilder"""
        return getUtility(IBuildQueueSet).getByBuilder(self)

    def requestAbort(self):
        """See IBuilder."""
        return self.slave.abort()

    def resumeSlaveHost(self):
        """See IBuilder."""
        logger = self._getSlaveScannerLogger()
        if not self.virtualized:
            raise CannotResumeHost('Builder is not virtualized.')

        if not self.vm_host:
            raise CannotResumeHost('Undefined vm_host.')

        logger.debug("Resuming %s", self.url)
        resume_command = config.builddmaster.vm_resume_command % {
            'vm_host': self.vm_host}
        resume_argv = resume_command.split()

        logger.debug('Running: %s', resume_argv)
        resume_process = subprocess.Popen(
            resume_argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = resume_process.communicate()

        if resume_process.returncode != 0:
            raise CannotResumeHost(
                "Resuming failed:\nOUT:\n%s\nERR:\n%s\n" % (stdout, stderr))
        return stdout, stderr

    @cachedproperty
    def slave(self):
        """See IBuilder."""
        # A cached attribute is used to allow tests to replace
        # the slave object, which is usually an XMLRPC client, with a
        # stub object that removes the need to actually create a buildd
        # slave in various states - which can be hard to create.
        return BuilderSlave(self.url)

    def setSlaveForTesting(self, new_slave):
        """See IBuilder."""
        self.slave = new_slave

    @property
    def pocket_dependencies(self):
        """A dictionary of pocket to possible pocket tuple.

        Return a dictionary that maps a pocket to pockets that it can
        depend on for a build.

        The dependencies apply equally no matter which archive type is
        using them; but some archives may not have builds in all the pockets.
        """
        return {
            PackagePublishingPocket.RELEASE :
                (PackagePublishingPocket.RELEASE,),
            PackagePublishingPocket.SECURITY :
                (PackagePublishingPocket.RELEASE,
                 PackagePublishingPocket.SECURITY),
            PackagePublishingPocket.UPDATES :
                (PackagePublishingPocket.RELEASE,
                 PackagePublishingPocket.SECURITY,
                 PackagePublishingPocket.UPDATES),
            PackagePublishingPocket.BACKPORTS :
                (PackagePublishingPocket.RELEASE,
                 PackagePublishingPocket.SECURITY,
                 PackagePublishingPocket.UPDATES,
                 PackagePublishingPocket.BACKPORTS),
            PackagePublishingPocket.PROPOSED :
                (PackagePublishingPocket.RELEASE,
                 PackagePublishingPocket.SECURITY,
                 PackagePublishingPocket.UPDATES,
                 PackagePublishingPocket.PROPOSED),
            }

    def _determineArchivesForBuild(self, build_queue_item):
        """Work out what sources.list lines should be passed to builder."""
        ogre_components = " ".join(build_queue_item.build.ogre_components)
        dist_name = build_queue_item.archseries.distroseries.name
        target_archive = build_queue_item.build.archive
        ubuntu_source_lines = []

        if (target_archive.purpose == ArchivePurpose.PARTNER or
            target_archive.purpose == ArchivePurpose.PPA):
            # Although partner and PPA builds are always in the release
            # pocket, they depend on the same pockets as though they
            # were in the updates pocket.
            #
            # XXX Julian 2008-03-20
            # Private PPAs, however, behave as though they are in the
            # security pocket.  This is a hack to get the security
            # PPA working as required until cprov lands his changes for
            # configurable PPA pocket dependencies.
            if target_archive.private:
                ubuntu_pockets = self.pocket_dependencies[
                    PackagePublishingPocket.SECURITY]
            else:
                ubuntu_pockets = self.pocket_dependencies[
                    PackagePublishingPocket.UPDATES]

            # Partner and PPA may also depend on any component.
            ubuntu_components = 'main restricted universe multiverse'

            # Calculate effects of current archive dependencies.
            archive_dependencies = [target_archive]
            archive_dependencies.extend(
                [dependency.dependency
                 for dependency in target_archive.dependencies])
            for archive in archive_dependencies:
                # Skip archives with no binaries published for the
                # target distroarchseries.
                published_binaries = archive.getAllPublishedBinaries(
                    distroarchseries=build_queue_item.archseries,
                    status=PackagePublishingStatus.PUBLISHED)
                if published_binaries.count() == 0:
                    continue

                # Encode the private PPA repository password in the
                # sources_list line. Note that the buildlog will be
                # sanitized to not expose it.
                if archive.private:
                    uri = URI(archive.archive_url)
                    uri = uri.replace(
                        userinfo="buildd:%s" % archive.buildd_secret)
                    url = str(uri)
                else:
                    url = archive.archive_url

                source_line = (
                    'deb %s %s %s'
                    % (url, dist_name, ogre_components))
                ubuntu_source_lines.append(source_line)
        else:
            ubuntu_pockets = self.pocket_dependencies[
                build_queue_item.build.pocket]
            ubuntu_components = ogre_components

        # Here we build a list of sources.list lines for each pocket
        # required in the primary archive.
        for pocket in ubuntu_pockets:
            if pocket == PackagePublishingPocket.RELEASE:
                dist_pocket = dist_name
            else:
                dist_pocket = dist_name + pocketsuffix[pocket]
            ubuntu_source_lines.append(
                'deb http://ftpmaster.internal/ubuntu %s %s'
                % (dist_pocket, ubuntu_components))

        return ubuntu_source_lines

    def _verifyBuildRequest(self, build_queue_item, logger):
        """Assert some pre-build checks.

        The build request is checked:
         * Virtualised builds can't build on a non-virtual builder
         * Ensure that we have a chroot
         * Ensure that the build pocket allows builds for the current
           distroseries state.
        """
        assert not (not self.virtualized and
                    build_queue_item.is_virtualized), (
            "Attempt to build non-virtual item on a virtual builder.")

        # Assert that we are not silently building SECURITY jobs.
        # See findBuildCandidates. Once we start building SECURITY
        # correctly from EMBARGOED archive this assertion can be removed.
        # XXX 2007-18-12 Julian. This is being addressed in the work on the
        # blueprint:
        # https://blueprints.launchpad.net/soyuz/+spec/security-in-soyuz
        target_pocket = build_queue_item.build.pocket
        assert target_pocket != PackagePublishingPocket.SECURITY, (
            "Soyuz is not yet capable of building SECURITY uploads.")

        # Ensure build has the needed chroot
        chroot = build_queue_item.archseries.getChroot()
        if chroot is None:
            raise CannotBuild(
                "Missing CHROOT for %s/%s/%s",
                build_queue_item.build.distroseries.distribution.name,
                build_queue_item.build.distroseries.name,
                build_queue_item.build.distroarchseries.architecturetag)

        # The main distribution has policies to prevent uploads to some
        # pockets (e.g. security) during different parts of the distribution
        # series lifecycle. These do not apply to PPA builds nor any archive
        # that allows release pocket updates.
        if (build_queue_item.build.archive.purpose != ArchivePurpose.PPA and
            not build_queue_item.build.archive.allowUpdatesToReleasePocket()):
            build = build_queue_item.build
            # XXX Robert Collins 2007-05-26: not an explicit CannotBuild
            # exception yet because the callers have not been audited
            assert build.distroseries.canUploadToPocket(build.pocket), (
                "%s (%s) can not be built for pocket %s: invalid pocket due "
                "to the series status of %s."
                % (build.title, build.id, build.pocket.name,
                   build.distroseries.name))

    def _dispatchBuildToSlave(self, build_queue_item, args, buildid, logger):
        """Start the build on the slave builder."""
        # Send chroot.
        chroot = build_queue_item.archseries.getChroot()
        self.cacheFileOnSlave(logger, chroot, False)

        # Build filemap structure with the files required in this build
        # and send them to the slave.
        filemap = {}
        for f in build_queue_item.files:
            filemap[f.libraryfile.filename] = f.libraryfile.content.sha1
            self.cacheFileOnSlave(
                logger, f.libraryfile, build_queue_item.build.archive.private)

        chroot_sha1 = chroot.content.sha1
        try:
            status, info = self.slave.build(
                buildid, "debian", chroot_sha1, filemap, args)
            message = """%s (%s):
            ***** RESULT *****
            %s
            %s
            %s: %s
            ******************
            """ % (self.name, self.url, filemap, args, status, info)
            logger.info(message)
        except (xmlrpclib.Fault, socket.error), info:
            # Mark builder as 'failed'.
            logger.debug(
                "Disabling builder: %s" % self.url, exc_info=1)
            self.failbuilder(
                "Exception (%s) when setting up to new job" % info)
            raise BuildSlaveFailure

    def startBuild(self, build_queue_item, logger):
        """See IBuilder."""
        logger.info("startBuild(%s, %s, %s, %s)", self.url,
                    build_queue_item.name, build_queue_item.version,
                    build_queue_item.build.pocket.title)

        # Make sure the request is valid; an exception is raised if it's not.
        self._verifyBuildRequest(build_queue_item, logger)

        # If we are building a virtual build, resume the virtual machine.
        if self.virtualized:
            self.resumeSlaveHost()

        # Build extra arguments.
        args = {}
        args["ogrecomponent"] = build_queue_item.build.current_component.name
        # turn 'arch_indep' ON only if build is archindep or if
        # the specific architecture is the nominatedarchindep for
        # this distroseries (in case it requires any archindep source)
        # XXX kiko 2006-08-31:
        # There is no point in checking if archhintlist ==
        # 'all' here, because it's redundant with the check for
        # isNominatedArchIndep.
        args['arch_indep'] = (
            build_queue_item.archhintlist == 'all' or
            build_queue_item.archseries.isNominatedArchIndep)
        args['archives'] = self._determineArchivesForBuild(build_queue_item)
        suite = build_queue_item.build.distroarchseries.distroseries.name
        if build_queue_item.build.pocket != PackagePublishingPocket.RELEASE:
            suite += "-%s" % (build_queue_item.build.pocket.name.lower())
        args['suite'] = suite
        archive_purpose = build_queue_item.build.archive.purpose.name
        args['archive_purpose'] = archive_purpose

        # Let the build slave know whether this is a build in a private
        # archive.
        args['archive_private'] = build_queue_item.build.archive.private

        # Generate a string which can be used to cross-check when obtaining
        # results so we know we are referring to the right database object in
        # subsequent runs.
        buildid = "%s-%s" % (build_queue_item.build.id, build_queue_item.id)
        logger.debug("Initiating build %s on %s" % (buildid, self.url))

        # Do it.
        build_queue_item.markAsBuilding(self)
        self._dispatchBuildToSlave(build_queue_item, args, buildid, logger)

    @property
    def status(self):
        """See IBuilder"""
        if self.manual:
            mode = 'MANUAL'
        else:
            mode = 'AUTO'

        if not self.builderok:
            return 'NOT OK : %s (%s)' % (self.failnotes, mode)

        if self.currentjob:
            current_build = self.currentjob.build
            msg = 'BUILDING %s' % current_build.title
            if current_build.archive.purpose == ArchivePurpose.PPA:
                archive_name = current_build.archive.owner.name
                return '%s [%s] (%s)' % (msg, archive_name, mode)
            return '%s (%s)' % (msg, mode)
        return 'IDLE (%s)' % mode

    def failbuilder(self, reason):
        """See IBuilder"""
        self.builderok = False
        self.failnotes = reason

    def getBuildRecords(self, build_state=None, name=None, user=None):
        """See IHasBuildRecords."""
        return getUtility(IBuildSet).getBuildsForBuilder(
            self.id, build_state, name, user)

    def slaveStatus(self):
        """See IBuilder."""
        builder_version, builder_arch, mechanisms = self.slave.info()
        status_sentence = self.slave.status()
        builder_status = status_sentence[0]

        if builder_status == 'BuilderStatus.WAITING':
            (build_status, build_id) = status_sentence[1:3]
            build_status_with_files = [
                'BuildStatus.OK',
                'BuildStatus.PACKAGEFAIL',
                'BuildStatus.DEPFAIL',
                ]
            if build_status in build_status_with_files:
                (filemap, dependencies) = status_sentence[3:]
            else:
                filemap = dependencies = None
            logtail = None
        elif builder_status == 'BuilderStatus.BUILDING':
            (build_id, logtail) = status_sentence[1:]
            build_status = filemap = dependencies = None
        else:
            build_id = status_sentence[1]
            build_status = logtail = filemap = dependencies = None

        return (builder_status, build_id, build_status, logtail, filemap,
                dependencies)

    def slaveStatusSentence(self):
        """See IBuilder."""
        return self.slave.status()

    def transferSlaveFileToLibrarian(self, file_sha1, filename):
        """See IBuilder."""
        out_file_fd, out_file_name = tempfile.mkstemp(suffix=".buildlog")
        out_file = os.fdopen(out_file_fd, "r+")
        try:
            slave_file = self.slave.getFile(file_sha1)
            copy_and_close(slave_file, out_file)
            # If the requested file is the 'buildlog' compress it using gzip
            # before storing in Librarian.
            if file_sha1 == 'buildlog':
                out_file = open(out_file_name)
                filename += '.gz'
                out_file_name += '.gz'
                gz_file = gzip.GzipFile(out_file_name, mode='wb')
                copy_and_close(out_file, gz_file)
                os.remove(out_file_name.replace('.gz', ''))

            # Reopen the file, seek to its end position, count and seek
            # to beginning, ready for adding to the Librarian.
            out_file = open(out_file_name)
            out_file.seek(0, 2)
            bytes_written = out_file.tell()
            out_file.seek(0)

            return getUtility(ILibrarianClient).addFile(filename,
                bytes_written, out_file,
                contentType=filenameToContentType(filename))
        finally:
            # Finally, remove the temporary file
            out_file.close()
            os.remove(out_file_name)

    @property
    def is_available(self):
        """See `IBuilder`."""
        if not self.builderok:
            return False
        try:
            slavestatus = self.slaveStatusSentence()
        except (xmlrpclib.Fault, socket.error), info:
            return False
        if slavestatus[0] != BuilderStatus.IDLE:
            return False
        return True

    # XXX cprov 20071116: It should become part of the public
    # findBuildCandidate once we start to detect superseded builds
    # at build creation time.
    def _findBuildCandidate(self):
        """Return the highest priority build candidate for this builder.

        Returns a pending IBuildQueue record queued for this builder
        processorfamily with the highest lastscore or None if there
        is no one available.
        """
        clauses = ["""
            buildqueue.build = build.id AND
            build.distroarchseries = distroarchseries.id AND
            build.archive = archive.id AND
            build.buildstate = %s AND
            distroarchseries.processorfamily = %s AND
            buildqueue.builder IS NULL
        """ % sqlvalues(BuildStatus.NEEDSBUILD, self.processor.family)]

        clauseTables = ['Build', 'DistroArchSeries', 'Archive']

        if not self.virtualized:
            clauses.append("""
                archive.purpose IN %s
            """ % sqlvalues([ArchivePurpose.PRIMARY, ArchivePurpose.PARTNER]))
        else:
            clauses.append("""
                archive.purpose = %s
            """ % sqlvalues(ArchivePurpose.PPA))

        query = " AND ".join(clauses)

        candidate = BuildQueue.selectFirst(
            query, clauseTables=clauseTables, prejoins=['build'],
            orderBy=['-buildqueue.lastscore'])

        return candidate

    def _getSlaveScannerLogger(self):
        """Return the logger instance from buildd-slave-scanner.py."""
        # XXX cprov 20071120: Ideally the Launchpad logging system
        # should be able to configure the root-logger instead of creating
        # a new object, then the logger lookups won't require the specific
        # name argument anymore. See bug 164203.
        logger = logging.getLogger('slave-scanner')
        return logger

    def findBuildCandidate(self):
        """See `IBuilder`."""
        logger = self._getSlaveScannerLogger()
        candidate = self._findBuildCandidate()

        # Mark build records targeted to old source versions as SUPERSEDED
        # and build records target to SECURITY pocket as FAILEDTOBUILD.
        # Builds in those situation should not be built because they will
        # be wasting build-time, the former case already has a newer source
        # and the latter could not be built in DAK.
        while candidate is not None:
            if candidate.build.pocket == PackagePublishingPocket.SECURITY:
                logger.debug(
                    "Build %s FAILEDTOBUILD, queue item %s REMOVED"
                    % (candidate.build.id, candidate.id))
                candidate.build.buildstate = BuildStatus.FAILEDTOBUILD
            elif candidate.is_last_version:
                return candidate
            else:
                logger.debug(
                    "Build %s SUPERSEDED, queue item %s REMOVED"
                    % (candidate.build.id, candidate.id))
                candidate.build.buildstate = BuildStatus.SUPERSEDED
            candidate.destroySelf()
            candidate = self._findBuildCandidate()

        # No candidate was found
        return None

    def dispatchBuildCandidate(self, candidate):
        """See `IBuilder`."""
        logger = self._getSlaveScannerLogger()
        try:
            self.startBuild(candidate, logger)
        except (BuildSlaveFailure, CannotBuild), err:
            logger.warn('Could not build: %s' % err)


class BuilderSet(object):
    """See IBuilderSet"""
    implements(IBuilderSet)

    def __init__(self):
        self.title = "The Launchpad build farm"

    def __iter__(self):
        return iter(Builder.select())

    def __getitem__(self, name):
        try:
            return Builder.selectOneBy(name=name)
        except SQLObjectNotFound:
            raise NotFoundError(name)

    def new(self, processor, url, name, title, description, owner,
            builderok=True, failnotes=None, virtualized=True, vm_host=None):
        """See IBuilderSet."""
        return Builder(processor=processor, url=url, name=name, title=title,
                       description=description, owner=owner,
                       virtualized=virtualized, builderok=builderok,
                       failnotes=failnotes, vm_host=None)

    def get(self, builder_id):
        """See IBuilderSet."""
        return Builder.get(builder_id)

    def count(self):
        """See IBuilderSet."""
        return Builder.select().count()

    def getBuilders(self):
        """See IBuilderSet."""
        return Builder.selectBy(active=True)

    def getBuildersByArch(self, arch):
        """See IBuilderSet."""
        return Builder.select('builder.processor = processor.id '
                              'AND processor.family = %d'
                              % arch.processorfamily.id,
                              clauseTables=("Processor",))

    def getBuildQueueSizeForProcessor(self, processor, virtualized=False):
        """See `IBuilderSet`."""
        if virtualized:
            archive_purposes = [ArchivePurpose.PPA]
        else:
            archive_purposes = [
                ArchivePurpose.PRIMARY, ArchivePurpose.PARTNER]

        query = """
           BuildQueue.build = Build.id AND
           Build.archive = Archive.id AND
           Build.distroarchseries = DistroArchSeries.id AND
           DistroArchSeries.processorfamily = Processor.family AND
           Processor.id = %s AND
           Build.buildstate = %s AND
           Archive.purpose IN %s
        """ % sqlvalues(processor, BuildStatus.NEEDSBUILD, archive_purposes)

        clauseTables = [
            'Build', 'DistroArchSeries', 'Processor', 'Archive']
        queue = BuildQueue.select(query, clauseTables=clauseTables)
        return queue.count()

    def pollBuilders(self, logger, txn):
        """See IBuilderSet."""
        logger.info("Slave Scan Process Initiated.")

        buildMaster = BuilddMaster(logger, txn)

        logger.info("Setting Builders.")
        # Put every distroarchseries we can find into the build master.
        for archseries in getUtility(IDistroArchSeriesSet):
            buildMaster.addDistroArchSeries(archseries)
            buildMaster.setupBuilders(archseries)

        logger.info("Scanning Builders.")
        # Scan all the pending builds, update logtails and retrieve
        # builds where they are completed
        buildMaster.scanActiveBuilders()
        return buildMaster

    def getBuildersForQueue(self, processor, virtualized):
        """See `IBuilderSet`."""
        return Builder.selectBy(builderok=True, processor=processor,
                                virtualized=virtualized)

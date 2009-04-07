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

from storm.store import Store

from canonical.cachedproperty import cachedproperty
from canonical.config import config
from canonical.buildd.slave import BuilderStatus
from canonical.buildmaster.master import BuilddMaster
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.components.archivedependencies import (
    get_primary_current_component, get_sources_list_for_building)
from canonical.launchpad.database.buildqueue import BuildQueue
from canonical.launchpad.database.publishing import makePoolPath
from lp.registry.interfaces.person import validate_public_person
from canonical.launchpad.helpers import filenameToContentType
from canonical.launchpad.interfaces import (
    ArchivePurpose, BuildDaemonError, BuildSlaveFailure, BuildStatus,
    CannotBuild, CannotResumeHost, IBuildQueueSet, IBuildSet,
    IBuilder, IBuilderSet, IDistroArchSeriesSet, IHasBuildRecords,
    ILibraryFileAliasSet, NotFoundError, PackagePublishingPocket,
    PackagePublishingStatus, ProtocolVersionMismatch)
from canonical.launchpad.webapp import urlappend
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

    def __init__(self, urlbase, vm_host):
        """Initialise a Server with specific parameter to our buildfarm."""
        self.vm_host = vm_host
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

    def resume(self):
        """Resume a virtual builder.

        It uses the configuration command-line (replacing 'vm_host') and
        return its output.

        :return: a (stdout, stderr, subprocess exitcode) triple
        """
        resume_command = config.builddmaster.vm_resume_command % {
            'vm_host': self.vm_host}
        resume_argv = resume_command.split()
        resume_process = subprocess.Popen(
            resume_argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = resume_process.communicate()

        return (stdout, stderr, resume_process.returncode)

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
        storm_validator=validate_public_person, notNull=True)
    builderok = BoolCol(dbName='builderok', notNull=True)
    failnotes = StringCol(dbName='failnotes')
    virtualized = BoolCol(dbName='virtualized', default=True, notNull=True)
    speedindex = IntCol(dbName='speedindex')
    manual = BoolCol(dbName='manual', default=False)
    vm_host = StringCol(dbName='vm_host')
    active = BoolCol(dbName='active', notNull=True, default=True)

    def cacheFileOnSlave(self, logger, libraryfilealias):
        """See `IBuilder`."""
        url = libraryfilealias.http_url
        logger.debug("Asking builder on %s to ensure it has file %s "
                     "(%s, %s)" % (self.url, libraryfilealias.filename,
                                   url, libraryfilealias.content.sha1))
        self._sendFileToSlave(url, libraryfilealias.content.sha1)

    def cachePrivateSourceOnSlave(self, logger, build_queue_item):
        """See `IBuilder`."""
        # The URL to the file in the archive consists of these parts:
        # archive_url / makePoolPath() / filename
        # Once this is constructed we add the http basic auth info.
        build = build_queue_item.build
        archive = build.archive
        archive_url = archive.archive_url
        component_name = build.current_component.name
        for source_file in build_queue_item.files:
            file_name = source_file.libraryfile.filename
            sha1 = source_file.libraryfile.content.sha1
            source_name = build.sourcepackagerelease.sourcepackagename.name
            poolpath = makePoolPath(source_name, component_name)
            url = urlappend(archive_url, poolpath)
            url = urlappend(url, file_name)
            logger.debug("Asking builder on %s to ensure it has file %s "
                         "(%s, %s)" % (self.url, file_name, url, sha1))
            self._sendFileToSlave(url, sha1, "buildd", archive.buildd_secret)

    def _sendFileToSlave(self, url, sha1, username="", password=""):
        """Helper to send the file at 'url' with 'sha1' to this builder."""
        if not self.builderok:
            raise BuildDaemonError("Attempted to give a file to a known-bad"
                                   " builder")
        present, info = self.slave.ensurepresent(
            sha1, url, username, password)
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
        if not self.virtualized:
            raise CannotResumeHost('Builder is not virtualized.')

        if not self.vm_host:
            raise CannotResumeHost('Undefined vm_host.')

        logger = self._getSlaveScannerLogger()
        logger.debug("Resuming %s (%s)" % (self.name, self.url))

        stdout, stderr, returncode = self.slave.resume()
        if returncode != 0:
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
        return BuilderSlave(self.url, self.vm_host)

    def setSlaveForTesting(self, proxy):
        """See IBuilder."""
        self.slave = proxy

    def _verifyBuildRequest(self, build_queue_item, logger):
        """Assert some pre-build checks.

        The build request is checked:
         * Virtualized builds can't build on a non-virtual builder
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
        # XXX Julian 2007-12-18 spec=security-in-soyuz: This is being
        # addressed in the work on the blueprint:
        # https://blueprints.launchpad.net/soyuz/+spec/security-in-soyuz
        target_pocket = build_queue_item.build.pocket
        assert target_pocket != PackagePublishingPocket.SECURITY, (
            "Soyuz is not yet capable of building SECURITY uploads.")

        # Ensure build has the needed chroot
        chroot = build_queue_item.archseries.getChroot()
        if chroot is None:
            raise CannotBuild(
                "Missing CHROOT for %s/%s/%s" % (
                    build_queue_item.build.distroseries.distribution.name,
                    build_queue_item.build.distroseries.name,
                    build_queue_item.build.distroarchseries.architecturetag)
                )

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
        self.cacheFileOnSlave(logger, chroot)

        # Build filemap structure with the files required in this build
        # and send them to the slave.
        # If the build is private we tell the slave to get the files from the
        # archive instead of the librarian because the slaves cannot
        # access the restricted librarian.
        private = build_queue_item.build.archive.private
        if private:
            self.cachePrivateSourceOnSlave(logger, build_queue_item)
        filemap = {}
        for source_file in build_queue_item.files:
            lfa = source_file.libraryfile
            filemap[lfa.filename] = lfa.content.sha1
            if not private:
                self.cacheFileOnSlave(logger, source_file.libraryfile)

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
        except xmlrpclib.Fault, info:
            # Mark builder as 'failed'.
            logger.debug("Disabling builder: %s" % self.url, exc_info=1)
            self.failbuilder(
                "Exception (%s) when setting up to new job" % info)
            raise BuildSlaveFailure
        except socket.error, info:
            error_message = "Exception (%s) when setting up new job" % info
            self.handleTimeout(logger, error_message)
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
        # turn 'arch_indep' ON only if build is archindep or if
        # the specific architecture is the nominatedarchindep for
        # this distroseries (in case it requires any archindep source)
        args['arch_indep'] = build_queue_item.archseries.isNominatedArchIndep

        suite = build_queue_item.build.distroarchseries.distroseries.name
        if build_queue_item.build.pocket != PackagePublishingPocket.RELEASE:
            suite += "-%s" % (build_queue_item.build.pocket.name.lower())
        args['suite'] = suite

        archive_purpose = build_queue_item.build.archive.purpose
        if (archive_purpose == ArchivePurpose.PPA and
            not build_queue_item.build.archive.require_virtualized):
            # If we're building a non-virtual PPA, override the purpose
            # to PRIMARY and use the primary component override.
            # This ensures that the package mangling tools will run over
            # the built packages.
            args['archive_purpose'] = ArchivePurpose.PRIMARY.name
            args["ogrecomponent"] = (
                get_primary_current_component(build_queue_item.build))
        else:
            args['archive_purpose'] = archive_purpose.name
            args["ogrecomponent"] = (
                build_queue_item.build.current_component.name)

        args['archives'] = get_sources_list_for_building(
            build_queue_item.build)

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
        if not self.builderok:
            if self.failnotes is not None:
                return self.failnotes
            return 'Disabled'
        # Cache the 'currentjob', so we don't have to hit the database
        # more than once.
        currentjob = self.currentjob
        if currentjob is None:
            return 'Idle'

        msg = 'Building %s' % currentjob.build.title
        if currentjob.build.archive.is_ppa:
            return '%s [%s]' % (msg, currentjob.build.archive.owner.name)
        if currentjob.build.archive.is_copy:
            return ('%s [%s/%s]' %
                    (msg, currentjob.build.archive.owner.name,
                     currentjob.build.archive.name))
        else:
            return msg

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

    def transferSlaveFileToLibrarian(self, file_sha1, filename, private):
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

            library_file = getUtility(ILibraryFileAliasSet).create(
                filename, bytes_written, out_file,
                contentType=filenameToContentType(filename),
                restricted=private)
        finally:
            # Finally, remove the temporary file
            out_file.close()
            os.remove(out_file_name)

        return library_file.id

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
        # If a private build does not yet have its source published then
        # we temporarily skip it because we want to wait for the publisher
        # to place the source in the archive, which is where builders
        # download the source from in the case of private builds (because
        # it's a secure location).
        private_statuses = (
            PackagePublishingStatus.PUBLISHED,
            PackagePublishingStatus.SUPERSEDED,
            PackagePublishingStatus.DELETED,
            )
        clauses = ["""
            ((archive.private IS TRUE AND
              EXISTS (
                  SELECT SourcePackagePublishingHistory.id
                  FROM SourcePackagePublishingHistory
                  WHERE
                      SourcePackagePublishingHistory.distroseries =
                         DistroArchSeries.distroseries AND
                      SourcePackagePublishingHistory.sourcepackagerelease =
                         Build.sourcepackagerelease AND
                      SourcePackagePublishingHistory.archive = Archive.id AND
                      SourcePackagePublishingHistory.status IN %s))
              OR
              archive.private IS FALSE) AND
            buildqueue.build = build.id AND
            build.distroarchseries = distroarchseries.id AND
            build.archive = archive.id AND
            archive.enabled = TRUE AND
            build.buildstate = %s AND
            distroarchseries.processorfamily = %s AND
            buildqueue.builder IS NULL
        """ % sqlvalues(private_statuses,
                        BuildStatus.NEEDSBUILD, self.processor.family)]

        clauseTables = ['Build', 'DistroArchSeries', 'Archive']

        clauses.append("""
            archive.require_virtualized = %s
        """ % sqlvalues(self.virtualized))

        query = " AND ".join(clauses)

        candidate = BuildQueue.selectFirst(
            query, clauseTables=clauseTables, prejoins=['build'],
            orderBy=['-buildqueue.lastscore', 'build.id'])

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
                # We never build anything in the security pocket.
                logger.debug(
                    "Build %s FAILEDTOBUILD, queue item %s REMOVED"
                    % (candidate.build.id, candidate.id))
                candidate.build.buildstate = BuildStatus.FAILEDTOBUILD
                candidate.destroySelf()
                candidate = self._findBuildCandidate()
                continue

            publication = candidate.build.getCurrentPublication()

            if publication is None:
                # The build should be superseded if it no longer has a
                # current publishing record.
                logger.debug(
                    "Build %s SUPERSEDED, queue item %s REMOVED"
                    % (candidate.build.id, candidate.id))
                candidate.build.buildstate = BuildStatus.SUPERSEDED
                candidate.destroySelf()
                candidate = self._findBuildCandidate()
                continue

            return candidate

        # No candidate was found.
        return None

    def dispatchBuildCandidate(self, candidate):
        """See `IBuilder`."""
        logger = self._getSlaveScannerLogger()
        try:
            self.startBuild(candidate, logger)
        except (BuildSlaveFailure, CannotBuild), err:
            logger.warn('Could not build: %s' % err)

    def handleTimeout(self, logger, error_message):
        """See IBuilder."""
        builder_should_be_failed = True

        if self.virtualized:
            # Virtualized/PPA builder: attempt a reset.
            logger.warn(
                "Resetting builder: %s -- %s" % (self.url, error_message),
                exc_info=True)
            try:
                self.resumeSlaveHost()
            except CannotResumeHost, err:
                # Failed to reset builder.
                logger.warn(
                    "Failed to reset builder: %s -- %s" %
                    (self.url, str(err)), exc_info=True)
            else:
                # Builder was reset, do *not* mark it as failed.
                builder_should_be_failed = False

        if builder_should_be_failed:
            # Mark builder as 'failed'.
            logger.warn(
                "Disabling builder: %s -- %s" % (self.url, error_message),
                exc_info=True)
            self.failbuilder(error_message)


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
            active=True, virtualized=False, vm_host=None):
        """See IBuilderSet."""
        return Builder(processor=processor, url=url, name=name, title=title,
                       description=description, owner=owner, active=active,
                       virtualized=virtualized, vm_host=vm_host,
                       builderok=True, manual=True)

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
        # Avoiding circular imports.
        from canonical.launchpad.database.archive import Archive
        from canonical.launchpad.database.build import Build
        from canonical.launchpad.database.distroarchseries import (
            DistroArchSeries)
        from canonical.launchpad.database.processor import Processor

        store = Store.of(processor)
        origin = (
            Archive,
            Build,
            BuildQueue,
            DistroArchSeries,
            Processor,
            )
        queue = store.using(*origin).find(
            BuildQueue,
            BuildQueue.build == Build.id,
            Build.distroarchseries == DistroArchSeries.id,
            Build.archive == Archive.id,
            DistroArchSeries.processorfamilyID == Processor.familyID,
            Build.buildstate == BuildStatus.NEEDSBUILD,
            Archive.enabled == True,
            Processor.id == processor.id,
            Archive.require_virtualized == virtualized,
            )

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

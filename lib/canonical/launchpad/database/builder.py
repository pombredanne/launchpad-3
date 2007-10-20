# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'Builder',
    'BuilderSet',
    ]

import httplib
import gzip
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
from canonical.buildmaster.master import BuilddMaster
from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.helpers import filenameToContentType
from canonical.launchpad.interfaces import (
    BuildDaemonError, BuildSlaveFailure, CannotBuild, CannotResetHost,
    IBuildQueueSet, IBuildSet, IBuilder, IBuilderSet, IDistroArchSeriesSet,
    IHasBuildRecords, NotFoundError,
    ProtocolVersionMismatch, pocketsuffix)
from canonical.launchpad.webapp import urlappend
from canonical.librarian.interfaces import ILibrarianClient
from canonical.librarian.utils import copy_and_close
from canonical.lp.dbschema import (
    ArchivePurpose, BuildStatus, PackagePublishingPocket)


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

    _defaultOrder = ['name']

    processor = ForeignKey(dbName='processor', foreignKey='Processor',
                           notNull=True)
    url = StringCol(dbName='url', notNull=True)
    name = StringCol(dbName='name', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    builderok = BoolCol(dbName='builderok', notNull=True)
    failnotes = StringCol(dbName='failnotes', default=None)
    trusted = BoolCol(dbName='trusted', default=False, notNull=True)
    speedindex = IntCol(dbName='speedindex', default=0)
    manual = BoolCol(dbName='manual', default=False)

    def cacheFileOnSlave(self, logger, libraryfilealias):
        """See IBuilder."""
        librarian = getUtility(ILibrarianClient)
        url = librarian.getURLForAlias(libraryfilealias.id, is_buildd=True)
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

    def resetSlaveHost(self, logger):
        """See IBuilder."""
        if self.trusted:
            # currently trusted builders cannot reset their host environment.
            raise CannotResetHost
        # XXX cprov 2007-05-10: Please FIX ME ASAP !
        # The ssh command line should be in the respective configuration
        # file. The builder XEN-host should be stored in DB (Builder.vmhost)
        # and not be calculated on the fly (this is gross).
        logger.debug("Resuming %s", self.url)
        hostname = self.url.split(':')[1][2:].split('.')[0]
        host_url = '%s-host.ppa' % hostname
        key_path = os.path.expanduser('~/.ssh/ppa-reset-builder')
        resume_argv = [
            'ssh', '-i' , key_path, 'ppa@%s' % host_url]
        logger.debug('Running: %s', resume_argv)
        resume_process = subprocess.Popen(
            resume_argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # XXX cprov 2007-06-15: If the reset command fails, we should raise
        # an error rather than assuming it reset ok.
        resume_process.communicate()

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

    @property
    def component_dependencies(self):
        """A dictionary of component to component dependencies.

        Return a dictionary that maps a component to a string of
        components that it is allowed to depend on for a build. This
        string can be used directly at the end of sources.list lines.
        """
        return {
            'main': 'main',
            'restricted': 'main restricted',
            'universe': 'main restricted universe',
            'multiverse': 'main restricted universe multiverse',
            'partner' : 'partner',
            }

    def _determineArchivesForBuild(self, build_queue_item):
        """Work out what sources.list lines should be passed to the builder."""
        ogre_components = self.component_dependencies[
            build_queue_item.build.current_component.name]
        dist_name = build_queue_item.archseries.distroseries.name
        archive_url = build_queue_item.build.archive.archive_url
        ubuntu_source_lines = []

        if (build_queue_item.build.archive.purpose == ArchivePurpose.PARTNER
            or
            build_queue_item.build.archive.purpose == ArchivePurpose.PPA):
            # Although partner and PPA builds are always in the release
            # pocket, they depend on the same pockets as though they
            # were in the updates pocket.
            ubuntu_pockets = self.pocket_dependencies[
                PackagePublishingPocket.UPDATES]

            # Partner and PPA may also depend on any component.
            ubuntu_components = 'main restricted universe multiverse'
            source_line = (
                'deb %s %s %s'
                % (archive_url, dist_name, ogre_components))
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
         * Untrusted builds can't build on a trusted builder
         * Ensure that we have a chroot
         * Ensure that the build pocket allows builds for the current
           distroseries state.
        """
        if self.trusted:
            assert build_queue_item.is_trusted, (
                "Attempt to build untrusted item on a trusted-only builder.")
        # Ensure build has the needed chroot
        chroot = build_queue_item.archseries.getChroot()
        if chroot is None:
            logger.debug("Missing CHROOT for %s/%s/%s",
                build_queue_item.build.distroseries.distribution.name,
                build_queue_item.build.distroseries.name,
                build_queue_item.build.distroarchseries.architecturetag)
            raise CannotBuild
        # The main distribution has policies prevent uploads to some pockets
        # (e.g. security) during different parts of the distribution series
        # lifecycle. These do not apply to PPA builds (which are untrusted)
        # nor any archive that allows release pocket updates.

        # XXX julian 2007-09-14
        # Currently is_trusted is being overloaded to also mean "is not a
        # PPA".  If we ever start building on machines outside our data
        # centre (ie not trusted) the following logic breaks.
        # https://bugs.launchpad.net/soyuz/+bug/139594
        if (build_queue_item.is_trusted and
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
        filemap = {}
        for f in build_queue_item.files:
            filemap[f.libraryfile.filename] = f.libraryfile.content.sha1
            self.cacheFileOnSlave(logger, f.libraryfile)

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
            self._logger.debug(
                "Disabling builder: %s" % self.url, exc_info=1)
            self.failbuilder("Exception (%s) when setting up to new job" % info)
            raise BuildSlaveFailure

    def startBuild(self, build_queue_item, logger):
        """See IBuilder."""
        logger.info("startBuild(%s, %s, %s, %s)", self.url,
                    build_queue_item.name, build_queue_item.version,
                    build_queue_item.build.pocket.title)

        # Make sure the request is valid; an exception is raised if it's not.
        self._verifyBuildRequest(build_queue_item, logger)

        # If we are building untrusted source reset the entire machine.
        if not self.trusted:
            self.resetSlaveHost(logger)

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
            if not current_build.is_trusted:
                archive_name = current_build.archive.owner.name
                return '%s [%s] (%s)' % (msg, archive_name, mode)
            return '%s (%s)' % (msg, mode)

        return 'IDLE (%s)' % mode

    def failbuilder(self, reason):
        """See IBuilder"""
        self.builderok = False
        self.failnotes = reason

    def getBuildRecords(self, build_state=None, name=None):
        """See IHasBuildRecords."""
        return getUtility(IBuildSet).getBuildsForBuilder(
            self.id, build_state, name)

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
        out_file_fd, out_file_name = tempfile.mkstemp(suffix=".tmp")
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
            builderok=True, failnotes=None, trusted=False):
        """See IBuilderSet."""
        return Builder(processor=processor, url=url, name=name, title=title,
                       description=description, owner=owner, trusted=trusted,
                       builderok=builderok, failnotes=failnotes)

    def get(self, builder_id):
        """See IBuilderSet."""
        return Builder.get(builder_id)

    def count(self):
        """See IBuilderSet."""
        return Builder.select().count()

    def getBuilders(self):
        """See IBuilderSet."""
        return Builder.select()

    def getBuildersByArch(self, arch):
        """See IBuilderSet."""
        return Builder.select('builder.processor = processor.id '
                              'AND processor.family = %d'
                              % arch.processorfamily.id,
                              clauseTables=("Processor",))

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

    def dispatchBuilds(self, logger, buildMaster):
        """See IBuilderSet."""
        buildCandidatesSortedByProcessor = buildMaster.sortAndSplitByProcessor()

        logger.info("Dispatching Jobs.")
        # Now that we've gathered in all the builds, dispatch the pending ones
        for candidate_proc in buildCandidatesSortedByProcessor.iteritems():
            processor, buildCandidates = candidate_proc
            buildMaster.dispatchByProcessor(processor, buildCandidates)

        logger.info("Slave Scan Process Finished.")

# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'Builder',
    'BuilderSet',
    ]

import httplib
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

from canonical.config import config
from canonical.buildmaster.master import BuilddMaster
from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.helpers import filenameToContentType
from canonical.launchpad.interfaces import (
    BuildDaemonError, BuildSlaveFailure, CannotBuild, CannotResetHost,
    IBuildQueueSet, IBuildSet, IBuilder, IBuilderSet, IDistroArchReleaseSet,
    IHasBuildRecords, NotFoundError,
    ProtocolVersionMismatch)
from canonical.launchpad.webapp import urlappend
from canonical.librarian.interfaces import ILibrarianClient
from canonical.librarian.utils import copy_and_close
from canonical.lp.dbschema import BuildStatus


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

    def checkCanBuildForDistroArchRelease(self, distro_arch_release):
        """See IBuilder."""
        # XXX: This function currently depends on the operating system specific
        # details of the build slave to return a processor-family-name (the
        # architecturetag) which matches the distro_arch_release. In reality,
        # we should be checking the processor itself (e.g. amd64) as that is
        # what the distro policy is set from, the architecture tag is both
        # distro specific and potentially different for radically different
        # distributions - its not the right thing to be comparing.

        # query the slave for its active details.
        # XXX: mechanisms is ignored? -- kiko
        builder_vers, builder_arch, mechanisms = self.slave.info()
        # we can only understand one version of slave today:
        if builder_vers != '1.0':
            raise ProtocolVersionMismatch("Protocol version mismatch")
        # check the slave arch-tag against the distro_arch_release.
        if builder_arch != distro_arch_release.architecturetag:
            raise BuildDaemonError(
                "Architecture tag mismatch: %s != %s"
                % (builder_arch, distro_arch_release.architecturetag))

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
        # XXX cprov 20070510: Please FIX ME ASAP !
        # The ssh command line should be in the respective configuration
        # file. The builder XEN-host should be stored in DB (Builder.vmhost)
        # and not be calculated on the fly (this is gross).
        logger.debug("Resuming %s", self.url)
        hostname = self.url.split(':')[1][2:].split('.')[0]
        host_url = '%s-host.ppa' % hostname
        resume_argv = [
            'ssh', '-i' , '~/.ssh/ppa-reset-builder', 'ppa@%s' % host_url]
        logger.debug('Running: %s', resume_argv)
        resume_process = subprocess.Popen(
            resume_argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        resume_process.communicate()
        # XXX: If the reset command fails, we should raise an error rather than
        # assuming it reset ok.

    @property
    def slave(self):
        """See IBuilder.

        A cached attribute _slave is used to allow tests to replace the _slave
        object, which is usually an XMLRPC client, with a stub object that
        removes the need to actually create a buildd slave in various states -
        which can be hard to create.
        """
        if getattr(self, '_slave', None) is None:
            self._slave = BuilderSlave(self.url)
        return self._slave

    def setSlaveForTesting(self, new_slave):
        """See IBuilder."""
        self._slave = new_slave

    def startBuild(self, build_queue_item, logger):
        """See IBuilder."""
        logger.info("startBuild(%s, %s, %s, %s)", self.url,
                    build_queue_item.name, build_queue_item.version,
                    build_queue_item.build.pocket.title)
        if self.trusted:
            assert build_queue_item.is_trusted, \
                "attempt to build untrusted item on a trusted-only builder."
        # ensure build has the need chroot
        chroot = build_queue_item.archrelease.getChroot(
            build_queue_item.build.pocket)
        if chroot is None:
            logger.debug("Missing CHROOT for %s/%s/%s/%s",
                build_queue_item.build.distrorelease.distribution.name,
                build_queue_item.build.distrorelease.name,
                build_queue_item.build.distroarchrelease.architecturetag,
                build_queue_item.build.pocket.name)
            raise CannotBuild
        # The main distribution has policies prevent uploads to some pockets
        # (e.g. security) during different parts of the distribution release
        # lifecycle. These do not apply to PPA builds (which are untrusted).
        if build_queue_item.is_trusted:
            build = build_queue_item.build
            # XXX: not an explicit CannotBuild exception yet because the callers
            # have not been audited - Robert Collins 20070526.
            assert build.distrorelease.canUploadToPocket(build.pocket), (
                "%s (%s) can not be built for pocket %s: invalid pocket due "
                "to the release status of %s."
                % (build.title, build.id, build.pocket.name,
                   build.distrorelease.name))
        # If we are building untrusted source reset the entire machine.
        if not self.trusted:
            self.resetSlaveHost(logger)
        # Send chroot.
        self.cacheFileOnSlave(logger, chroot)
        # Build filemap structure with the files required in this build
        # and send them to the slave.
        filemap = {}
        for f in build_queue_item.files:
            filemap[f.libraryfile.filename] = f.libraryfile.content.sha1
            self.cacheFileOnSlave(logger, f.libraryfile)
        # Build extra arguments
        args = {}
        args["ogrecomponent"] = build_queue_item.component_name
        # turn 'arch_indep' ON only if build is archindep or if
        # the specific architecture is the nominatedarchindep for
        # this distrorelease (in case it requires any archindep source)
        # XXX: there is no point in checking if archhintlist ==
        # 'all' here, because it's redundant with the check for
        # isNominatedArchIndep. -- kiko, 2006-08-31
        args['arch_indep'] = (
            build_queue_item.archhintlist == 'all' or
            build_queue_item.archrelease.isNominatedArchIndep)

        if not build_queue_item.is_trusted:
            # Add the urls for the current published archives to the build
            # so that dependencies can be downloaded correctly.
            # Only provide access to the minimal set of components required
            # to be present by the component the build_queue_item is for.
            components_map = {
                'main': 'main',
                'restricted': 'main restricted',
                'universe': 'main restricted universe',
                'multiverse': 'main restricted universe multiverse',
                }
            allowed_components = components_map[
                build_queue_item.component_name]
            args['archives'] = [
                'http://archive.ubuntu.com/ubuntu %s' % allowed_components,
                '%s/ubuntu %s' % (
                    build_queue_item.build.archive.archive_url,
                    allowed_components)
                ]
        else:
            # Use the default archives generated by the build environment.
            args['archives'] = []

        chroot_sha1 = chroot.content.sha1
        # store DB information
        build_queue_item.builder = self
        build_queue_item.buildstart = UTC_NOW
        build_queue_item.build.buildstate = BuildStatus.BUILDING
        # Generate a string which can be used to cross-check when obtaining
        # results so we know we are referring to the right database object in
        # subsequent runs.
        buildid = "%s-%s" % (build_queue_item.build.id, build_queue_item.id)
        logger.debug("Initiating build %s on %s" % (buildid, self.url))
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
            # mark builder as 'failed'.
            self._logger.debug(
                "Disabling builder: %s" % self.url, exc_info=1)
            self.failbuilder("Exception (%s) when setting up to new job" % info)
            raise BuildSlaveFailure

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

    def getBuildRecords(self, status=None, name=None):
        """See IHasBuildRecords."""
        return getUtility(IBuildSet).getBuildsForBuilder(self.id, status, name)

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
        # ensure the tempfile will return a proper name, which does not
        # confuses the gzip as suffixes like '-Z', '-z', almost everything
        # insanely related to 'z'. Might also be solved by bug # 3111
        out_file_fd, out_file_name = tempfile.mkstemp(suffix=".tmp")
        out_file = os.fdopen(out_file_fd, "r+")
        try:
            slave_file = self.slave.getFile(file_sha1)
            copy_and_close(slave_file, out_file)
            # if the requested file is the 'buildlog' compress it using gzip
            # before storing in Librarian
            if file_sha1 == 'buildlog':
                # XXX cprov 20051010:
                # python.gzip presented weird errors at this point, most
                # related to incomplete file storage, the compressed file
                # was prematurely finished in a 0x00. Using system call as a
                # workaround until bug #3111 is addressed.
                os.system('gzip -9 %s' % out_file_name)
                # modify the local and header filename
                filename += '.gz'
                out_file_name += '.gz'

            # reopen the file, seek to its end position, count and seek
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
        # Put every distroarchrelease we can find into the build master.
        for archrelease in getUtility(IDistroArchReleaseSet):
            buildMaster.addDistroArchRelease(archrelease)
            buildMaster.setupBuilders(archrelease)

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

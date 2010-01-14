# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

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
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    BuildBehaviorMismatch)
from lp.buildmaster.master import BuilddMaster
from lp.buildmaster.model.buildfarmjobbehavior import IdleBuildBehavior
from canonical.database.sqlbase import SQLBase, sqlvalues

# XXX Michael Nelson 2010-01-13 bug=491330,506617
# These dependencies on soyuz will be removed when getBuildRecords()
# is moved, as well as when the generalisation of findBuildCandidate()
# is completed.
from lp.soyuz.model.buildqueue import BuildQueue, specific_job_classes
from lp.registry.interfaces.person import validate_public_person
from canonical.launchpad.helpers import filenameToContentType
from lp.services.job.interfaces.job import JobStatus
from lp.soyuz.interfaces.buildrecords import IHasBuildRecords
from lp.soyuz.interfaces.distroarchseries import IDistroArchSeriesSet
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.webapp.interfaces import NotFoundError
from lp.soyuz.interfaces.build import BuildStatus, IBuildSet
from lp.buildmaster.interfaces.builder import (
    BuildDaemonError, BuildSlaveFailure, CannotBuild, CannotFetchFile,
    CannotResumeHost, IBuilder, IBuilderSet, ProtocolVersionMismatch)
from lp.soyuz.interfaces.buildqueue import IBuildQueueSet
from lp.soyuz.model.buildpackagejob import BuildPackageJob
from canonical.launchpad.webapp import urlappend
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.lazr.utils import safe_hasattr
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


class BuilderSlave(xmlrpclib.ServerProxy):
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

    def cacheFile(self, logger, libraryfilealias):
        """Make sure that the file at 'libraryfilealias' is on the slave.

        :param logger: A python `Logger` object.
        :param libraryfilealias: An `ILibraryFileAlias`.
        """
        url = libraryfilealias.http_url
        logger.debug("Asking builder on %s to ensure it has file %s "
                     "(%s, %s)" % (self.urlbase, libraryfilealias.filename,
                                   url, libraryfilealias.content.sha1))
        self._sendFileToSlave(url, libraryfilealias.content.sha1)

    def _sendFileToSlave(self, url, sha1, username="", password=""):
        """Helper to send the file at 'url' with 'sha1' to this builder."""
        present, info = self.ensurepresent(sha1, url, username, password)
        if not present:
            raise CannotFetchFile(url, info)

    def build(self, buildid, builder_type, chroot_sha1, filemap, args):
        """Build a thing on this build slave.

        :param buildid: A string identifying this build.
        :param builder_type: The type of builder needed.
        :param chroot_sha1: XXX
        :param filemap: A dictionary mapping from paths to SHA-1 hashes of
            the file contents.
        :param args: A dictionary of extra arguments. The contents depend on
            the build job type.
        """
        # Can't upcall to xmlrpclib.ServerProxy, since it doesn't actually
        # have a 'build' method.
        build_method = xmlrpclib.ServerProxy.__getattr__(self, 'build')
        try:
            return build_method(
                self, buildid, builder_type, chroot_sha1, filemap, args)
        except xmlrpclib.Fault, info:
            raise BuildSlaveFailure(info)


class Builder(SQLBase):

    implements(IBuilder, IHasBuildRecords)
    _table = 'Builder'

    _defaultOrder = ['id']

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

    def _getCurrentBuildBehavior(self):
        """Return the current build behavior."""
        if not safe_hasattr(self, '_current_build_behavior'):
            self._current_build_behavior = None

        if (self._current_build_behavior is None or
            isinstance(self._current_build_behavior, IdleBuildBehavior)):
            # If we don't currently have a current build behavior set,
            # or we are currently idle, then...
            currentjob = self.currentjob
            if currentjob is not None:
                # ...we'll set it based on our current job.
                self._current_build_behavior = (
                    currentjob.required_build_behavior)
                self._current_build_behavior.setBuilder(self)
                return self._current_build_behavior
            elif self._current_build_behavior is None:
                # If we don't have a current job or an idle behavior
                # already set, then we just set the idle behavior
                # before returning.
                self._current_build_behavior = IdleBuildBehavior()
            return self._current_build_behavior

        else:
            # We did have a current non-idle build behavior set, so
            # we just return it.
            return self._current_build_behavior

    def _setCurrentBuildBehavior(self, new_behavior):
        """Set the current build behavior."""
        self._current_build_behavior = new_behavior
        if self._current_build_behavior is not None:
            self._current_build_behavior.setBuilder(self)

    current_build_behavior = property(
        _getCurrentBuildBehavior, _setCurrentBuildBehavior)

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

    def startBuild(self, build_queue_item, logger):
        """See IBuilder."""
        self.current_build_behavior = build_queue_item.required_build_behavior
        self.current_build_behavior.logStartBuild(logger)

        # Make sure the request is valid; an exception is raised if it's not.
        self.current_build_behavior.verifyBuildRequest(logger)

        # Set the build behavior depending on the provided build queue item.
        if not self.builderok:
            raise BuildDaemonError(
                "Attempted to start a build on a known-bad builder.")

        # If we are building a virtual build, resume the virtual machine.
        if self.virtualized:
            self.resumeSlaveHost()

        # Do it.
        build_queue_item.markAsBuilding(self)
        try:
            self.current_build_behavior.dispatchBuildToSlave(
                build_queue_item.id, logger)
        except BuildSlaveFailure, e:
            logger.debug("Disabling builder: %s" % self.url, exc_info=1)
            self.failbuilder(
                "Exception (%s) when setting up to new job" % (e,))
        except CannotFetchFile, e:
            message = """Slave '%s' (%s) was unable to fetch file.
            ****** URL ********
            %s
            ****** INFO *******
            %s
            *******************
            """ % (self.name, self.url, e.file_url, e.error_information)
            raise BuildDaemonError(message)
        except socket.error, e:
            error_message = "Exception (%s) when setting up new job" % (e,)
            self.handleTimeout(logger, error_message)
            raise BuildSlaveFailure

    def failbuilder(self, reason):
        """See IBuilder"""
        self.builderok = False
        self.failnotes = reason

    # XXX Michael Nelson 20091202 bug=491330. The current UI assumes
    # that the builder history will display binary build records, as
    # returned by getBuildRecords() below. See the bug for a discussion
    # of the options.

    def getBuildRecords(self, build_state=None, name=None, arch_tag=None,
                        user=None):
        """See IHasBuildRecords."""
        return getUtility(IBuildSet).getBuildsForBuilder(
            self.id, build_state, name, arch_tag, user)

    def slaveStatus(self):
        """See IBuilder."""
        builder_version, builder_arch, mechanisms = self.slave.info()
        status_sentence = self.slave.status()

        status = {'builder_status': status_sentence[0]}
        status.update(
            self.current_build_behavior.slaveStatus(status_sentence))
        return status

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
        except (xmlrpclib.Fault, socket.error):
            return False
        if slavestatus[0] != BuilderStatus.IDLE:
            return False
        return True

    def _getSlaveScannerLogger(self):
        """Return the logger instance from buildd-slave-scanner.py."""
        # XXX cprov 20071120: Ideally the Launchpad logging system
        # should be able to configure the root-logger instead of creating
        # a new object, then the logger lookups won't require the specific
        # name argument anymore. See bug 164203.
        logger = logging.getLogger('slave-scanner')
        return logger

    def _findBuildCandidate(self):
        """Find a candidate job for dispatch to an idle buildd slave.

        The pending BuildQueue item with the highest score for this builder
        or None if no candidate is available.

        :return: A candidate job.
        """
        def qualify_subquery(job_type, sub_query):
            """Put the sub-query into a job type context."""
            qualified_query = """
                ((BuildQueue.job_type != %s) OR (%%s))
            """ % sqlvalues(job_type)
            qualified_query %= sub_query
            return qualified_query

        logger = self._getSlaveScannerLogger()
        candidate = None

        query_tables = set(('buildqueue', 'job'))
        general_query = """
            SELECT buildqueue.id FROM %%s
            WHERE
                buildqueue.job = job.id
                AND job.status = %s
                AND (
                    (buildqueue.processor = %s
                     AND buildqueue.virtualized = %s)
                   OR
                    (buildqueue.processor IS NULL
                     AND buildqueue.virtualized IS NULL))
                AND buildqueue.builder IS NULL
        """ % sqlvalues(JobStatus.WAITING, self.processor, self.virtualized)
        order_clause = " ORDER BY buildqueue.lastscore DESC, buildqueue.id"

        extra_tables = set()
        extra_queries = []
        job_classes = specific_job_classes()
        for job_type, job_class in job_classes.iteritems():
            tables, query = job_class.addCandidateSelectionCriteria(
                self.processor, self.virtualized)
            if query == '':
                # This job class does not need to refine candidate jobs
                # further.
                continue

            # Table names are case-insensitive in SQL. All table names are in
            # lower case in order to avoid duplicates in the FROM clause.
            query_tables = query_tables.union(
                set(table.lower() for table in tables))
            # The sub-query should only apply to jobs of the right type.
            extra_queries.append(qualify_subquery(job_type, query))
        general_query = general_query % ', '.join(query_tables)
        query = ' AND '.join([general_query] + extra_queries) + order_clause

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        candidate_jobs = store.execute(query).get_all()

        for (candidate_id,) in candidate_jobs:
            candidate = getUtility(IBuildQueueSet).get(candidate_id)
            job_class = job_classes[candidate.job_type]
            candidate_approved = job_class.postprocessCandidate(
                candidate, logger)
            if candidate_approved:
                return candidate

        return None

    def _dispatchBuildCandidate(self, candidate):
        """Dispatch the pending job to the associated buildd slave.

        This method can only be executed in the builddmaster machine, since
        it will actually issues the XMLRPC call to the buildd-slave.

        :param candidate: The job to dispatch.
        """
        logger = self._getSlaveScannerLogger()
        try:
            self.startBuild(candidate, logger)
        except (BuildSlaveFailure, CannotBuild, BuildBehaviorMismatch), err:
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

    def findAndStartJob(self, buildd_slave=None):
        """See IBuilder."""
        logger = self._getSlaveScannerLogger()
        candidate = self._findBuildCandidate()

        if candidate is None:
            logger.debug("No build candidates available for builder.")
            return None

        if buildd_slave is not None:
            self.setSlaveForTesting(buildd_slave)

        self._dispatchBuildCandidate(candidate)
        return candidate


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
        return Builder.selectBy(
            active=True, orderBy=['virtualized', 'processor', 'name'])

    def getBuildersByArch(self, arch):
        """See IBuilderSet."""
        return Builder.select('builder.processor = processor.id '
                              'AND processor.family = %d'
                              % arch.processorfamily.id,
                              clauseTables=("Processor",))

    def getBuildQueueSizeForProcessor(self, processor, virtualized=False):
        """See `IBuilderSet`."""
        # Avoiding circular imports.
        from lp.soyuz.model.archive import Archive
        from lp.soyuz.model.build import Build
        from lp.soyuz.model.distroarchseries import (
            DistroArchSeries)
        from lp.soyuz.model.processor import Processor

        store = Store.of(processor)
        origin = (
            Archive,
            Build,
            BuildPackageJob,
            BuildQueue,
            DistroArchSeries,
            Processor,
            )
        queue = store.using(*origin).find(
            BuildQueue,
            BuildPackageJob.job == BuildQueue.jobID,
            BuildPackageJob.build == Build.id,
            Build.distroarchseries == DistroArchSeries.id,
            Build.archive == Archive.id,
            DistroArchSeries.processorfamilyID == Processor.familyID,
            Build.buildstate == BuildStatus.NEEDSBUILD,
            Archive._enabled == True,
            Processor.id == processor.id,
            Archive.require_virtualized == virtualized,
            )

        return (queue.count(), queue.sum(BuildQueue.estimated_duration))

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

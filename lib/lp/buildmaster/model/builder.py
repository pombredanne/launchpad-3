# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = [
    'Builder',
    'BuilderSet',
    'ProxyWithConnectionTimeout',
    'rescueBuilderIfLost',
    'updateBuilderStatus',
    ]

import gzip
import logging
import os
import socket
import tempfile
import xmlrpclib

from lazr.restful.utils import safe_hasattr
from sqlobject import (
    BoolCol,
    ForeignKey,
    IntCol,
    SQLObjectNotFound,
    StringCol,
    )
from storm.expr import (
    Coalesce,
    Count,
    Sum,
    )
import transaction
from twisted.internet import (
    defer,
    reactor as default_reactor,
    )
from twisted.web import xmlrpc
from twisted.web.client import downloadPage
from zope.component import getUtility
from zope.interface import implements

from canonical.buildd.slave import BuilderStatus
from canonical.config import config
from canonical.database.sqlbase import (
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.helpers import filenameToContentType
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.webapp import urlappend
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    SLAVE_FLAVOR,
    )
from canonical.librarian.utils import copy_and_close
from lp.app.errors import NotFoundError
from lp.buildmaster.interfaces.builder import (
    BuildDaemonError,
    BuildSlaveFailure,
    CannotFetchFile,
    CannotResumeHost,
    CorruptBuildCookie,
    IBuilder,
    IBuilderSet,
    )
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobSet
from lp.buildmaster.interfaces.buildqueue import IBuildQueueSet
from lp.buildmaster.model.buildfarmjobbehavior import IdleBuildBehavior
from lp.buildmaster.model.buildqueue import (
    BuildQueue,
    specific_job_classes,
    )
from lp.registry.interfaces.person import validate_public_person
from lp.services.database.transaction_policy import DatabaseTransactionPolicy
from lp.services.job.interfaces.job import JobStatus
from lp.services.job.model.job import Job
from lp.services.propertycache import cachedproperty
from lp.services.twistedsupport import cancel_on_timeout
from lp.services.twistedsupport.processmonitor import ProcessWithTimeout
# XXX Michael Nelson 2010-01-13 bug=491330
# These dependencies on soyuz will be removed when getBuildRecords()
# is moved.
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuildSet
from lp.soyuz.interfaces.buildrecords import (
    IHasBuildRecords,
    IncompatibleArguments,
    )
from lp.soyuz.model.processor import Processor


class QuietQueryFactory(xmlrpc._QueryFactory):
    """XMLRPC client factory that doesn't splatter the log with junk."""
    noisy = False


class ProxyWithConnectionTimeout(xmlrpc.Proxy):
    """Extend Twisted's Proxy to provide a configurable connection timeout."""

    def __init__(self, url, user=None, password=None, allowNone=False,
                 useDateTime=False, timeout=None):
        xmlrpc.Proxy.__init__(
            self, url, user, password, allowNone, useDateTime)
        if timeout is None:
            self.timeout = config.builddmaster.socket_timeout
        else:
            self.timeout = timeout

    def callRemote(self, method, *args):
        """Basically a carbon copy of the parent but passes the timeout
        to connectTCP."""

        def cancel(d):
            factory.deferred = None
            connector.disconnect()
        factory = self.queryFactory(
            self.path, self.host, method, self.user,
            self.password, self.allowNone, args, cancel, self.useDateTime)
        if self.secure:
            from twisted.internet import ssl
            connector = default_reactor.connectSSL(
                self.host, self.port or 443, factory,
                ssl.ClientContextFactory(),
                timeout=self.timeout)
        else:
            connector = default_reactor.connectTCP(
                self.host, self.port or 80, factory,
                timeout=self.timeout)
        return factory.deferred


class BuilderSlave(object):
    """Add in a few useful methods for the XMLRPC slave.

    :ivar url: The URL of the actual builder. The XML-RPC resource and
        the filecache live beneath this.
    """

    # WARNING: If you change the API for this, you should also change the APIs
    # of the mocks in soyuzbuilderhelpers to match. Otherwise, you will have
    # many false positives in your test run and will most likely break
    # production.

    def __init__(self, proxy, builder_url, vm_host, reactor=None):
        """Initialize a BuilderSlave.

        :param proxy: An XML-RPC proxy, implementing 'callRemote'. It must
            support passing and returning None objects.
        :param builder_url: The URL of the builder.
        :param vm_host: The VM host to use when resuming.
        """
        self.url = builder_url
        self._vm_host = vm_host
        self._file_cache_url = urlappend(builder_url, 'filecache')
        self._server = proxy

        if reactor is None:
            self.reactor = default_reactor
        else:
            self.reactor = reactor

    @classmethod
    def makeBuilderSlave(cls, builder_url, vm_host, reactor=None, proxy=None):
        """Create and return a `BuilderSlave`.

        :param builder_url: The URL of the slave buildd machine,
            e.g. http://localhost:8221
        :param vm_host: If the slave is virtual, specify its host machine
            here.
        :param reactor: Used by tests to override the Twisted reactor.
        :param proxy: Used By tests to override the xmlrpc.Proxy.
        """
        rpc_url = urlappend(builder_url.encode('utf-8'), 'rpc')
        if proxy is None:
            server_proxy = ProxyWithConnectionTimeout(rpc_url, allowNone=True)
            server_proxy.queryFactory = QuietQueryFactory
        else:
            server_proxy = proxy
        return cls(server_proxy, builder_url, vm_host, reactor)

    def _with_timeout(self, d):
        TIMEOUT = config.builddmaster.socket_timeout
        return cancel_on_timeout(d, TIMEOUT, self.reactor)

    def abort(self):
        """Abort the current build."""
        return self._with_timeout(self._server.callRemote('abort'))

    def clean(self):
        """Clean up the waiting files and reset the slave's internal state."""
        return self._with_timeout(self._server.callRemote('clean'))

    def echo(self, *args):
        """Echo the arguments back."""
        return self._with_timeout(self._server.callRemote('echo', *args))

    def info(self):
        """Return the protocol version and the builder methods supported."""
        return self._with_timeout(self._server.callRemote('info'))

    def status(self):
        """Return the status of the build daemon."""
        return self._with_timeout(self._server.callRemote('status'))

    def ensurepresent(self, sha1sum, url, username, password):
        # XXX: Nothing external calls this. Make it private.
        """Attempt to ensure the given file is present."""
        return self._with_timeout(self._server.callRemote(
            'ensurepresent', sha1sum, url, username, password))

    def getFile(self, sha_sum, file_to_write):
        """Fetch a file from the builder.

        :param sha_sum: The sha of the file (which is also its name on the
            builder)
        :param file_to_write: A file name or file-like object to write
            the file to
        :return: A Deferred that calls back when the download is done, or
            errback with the error string.
        """
        file_url = urlappend(self._file_cache_url, sha_sum).encode('utf8')
        # If desired we can pass a param "timeout" here but let's leave
        # it at the default value if it becomes obvious we need to
        # change it.
        return downloadPage(file_url, file_to_write, followRedirect=0)

    def getFiles(self, filemap):
        """Fetch many files from the builder.

        :param filemap: A Dictionary containing key values of the builder
            file name to retrieve, which maps to a value containing the
            file name or file object to write the file to.

        :return: A DeferredList that calls back when the download is done.
        """
        dl = defer.gatherResults([
            self.getFile(builder_file, filemap[builder_file])
            for builder_file in filemap])
        return dl

    def resume(self, clock=None):
        """Resume the builder in an asynchronous fashion.

        We use the builddmaster configuration 'socket_timeout' as
        the process timeout.

        :param clock: An optional twisted.internet.task.Clock to override
                      the default clock.  For use in tests.

        :return: a Deferred that returns a
            (stdout, stderr, subprocess exitcode) triple
        """
        resume_command = config.builddmaster.vm_resume_command % {
            'vm_host': self._vm_host}
        # Twisted API requires string but the configuration provides unicode.
        resume_argv = [
            term.encode('utf-8') for term in resume_command.split()]
        d = defer.Deferred()
        p = ProcessWithTimeout(
            d, config.builddmaster.socket_timeout, clock=clock)
        p.spawnProcess(resume_argv[0], tuple(resume_argv))
        return d

    def cacheFile(self, logger, libraryfilealias):
        """Make sure that the file at 'libraryfilealias' is on the slave.

        :param logger: A python `Logger` object.
        :param libraryfilealias: An `ILibraryFileAlias`.
        """
        url = libraryfilealias.http_url
        logger.info(
            "Asking builder on %s to ensure it has file %s (%s, %s)" % (
                self._file_cache_url, libraryfilealias.filename, url,
                libraryfilealias.content.sha1))
        return self.sendFileToSlave(libraryfilealias.content.sha1, url)

    def sendFileToSlave(self, sha1, url, username="", password=""):
        """Helper to send the file at 'url' with 'sha1' to this builder."""
        d = self.ensurepresent(sha1, url, username, password)

        def check_present((present, info)):
            if not present:
                raise CannotFetchFile(url, info)
        return d.addCallback(check_present)

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
        d = self._with_timeout(self._server.callRemote(
            'build', buildid, builder_type, chroot_sha1, filemap, args))

        def got_fault(failure):
            failure.trap(xmlrpclib.Fault)
            raise BuildSlaveFailure(failure.value)
        return d.addErrback(got_fault)


# This is a separate function since MockBuilder needs to use it too.
# Do not use it -- (Mock)Builder.rescueIfLost should be used instead.
def rescueBuilderIfLost(builder, logger=None):
    """See `IBuilder`."""
    # 'ident_position' dict relates the position of the job identifier
    # token in the sentence received from status(), according the
    # two status we care about. See see lib/canonical/buildd/slave.py
    # for further information about sentence format.
    ident_position = {
        'BuilderStatus.BUILDING': 1,
        'BuilderStatus.WAITING': 2
        }

    d = builder.slaveStatusSentence()

    def got_status(status_sentence):
        """After we get the status, clean if we have to.

        Always return status_sentence.
        """
        # Isolate the BuilderStatus string, always the first token in
        # see lib/canonical/buildd/slave.py and
        # IBuilder.slaveStatusSentence().
        status = status_sentence[0]

        # If the cookie test below fails, it will request an abort of the
        # builder.  This will leave the builder in the aborted state and
        # with no assigned job, and we should now "clean" the slave which
        # will reset its state back to IDLE, ready to accept new builds.
        # This situation is usually caused by a temporary loss of
        # communications with the slave and the build manager had to reset
        # the job.
        if status == 'BuilderStatus.ABORTED' and builder.currentjob is None:
            if not builder.virtualized:
                # We can't reset non-virtual builders reliably as the
                # abort() function doesn't kill the actual build job,
                # only the sbuild process!  All we can do here is fail
                # the builder with a message indicating the problem and
                # wait for an admin to reboot it.
                builder.failBuilder(
                    "Non-virtual builder in ABORTED state, requires admin to "
                    "restart")
                return "dummy status"
            if logger is not None:
                logger.info(
                    "Builder '%s' being cleaned up from ABORTED" %
                    (builder.name,))
            d = builder.cleanSlave()
            return d.addCallback(lambda ignored: status_sentence)
        else:
            return status_sentence

    def rescue_slave(status_sentence):
        # If slave is not building nor waiting, it's not in need of rescuing.
        status = status_sentence[0]
        if status not in ident_position.keys():
            return
        slave_build_id = status_sentence[ident_position[status]]
        try:
            builder.verifySlaveBuildCookie(slave_build_id)
        except CorruptBuildCookie, reason:
            if status == 'BuilderStatus.WAITING':
                d = builder.cleanSlave()
            else:
                d = builder.requestAbort()

            def log_rescue(ignored):
                if logger:
                    logger.info(
                        "Builder '%s' rescued from '%s': '%s'" %
                        (builder.name, slave_build_id, reason))
            return d.addCallback(log_rescue)

    d.addCallback(got_status)
    d.addCallback(rescue_slave)
    return d


def updateBuilderStatus(builder, logger=None):
    """See `IBuilder`."""
    if logger:
        logger.debug('Checking %s' % builder.name)

    return builder.rescueIfLost(logger)


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
    _builderok = BoolCol(dbName='builderok', notNull=True)
    failnotes = StringCol(dbName='failnotes')
    virtualized = BoolCol(dbName='virtualized', default=True, notNull=True)
    speedindex = IntCol(dbName='speedindex')
    manual = BoolCol(dbName='manual', default=False)
    vm_host = StringCol(dbName='vm_host')
    active = BoolCol(dbName='active', notNull=True, default=True)
    failure_count = IntCol(dbName='failure_count', default=0, notNull=True)

    # The number of times a builder can consecutively fail before we
    # give up and mark it builderok=False.
    FAILURE_THRESHOLD = 5

    def __storm_invalidated__(self):
        """Clear cached properties."""
        super(Builder, self).__storm_invalidated__()
        self._current_build_behavior = None

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

    def _getBuilderok(self):
        return self._builderok

    def _setBuilderok(self, value):
        self._builderok = value
        if value is True:
            self.resetFailureCount()

    builderok = property(_getBuilderok, _setBuilderok)

    def gotFailure(self):
        """See `IBuilder`."""
        self.failure_count += 1

    def resetFailureCount(self):
        """See `IBuilder`."""
        self.failure_count = 0

    def rescueIfLost(self, logger=None):
        """See `IBuilder`."""
        return rescueBuilderIfLost(self, logger)

    def updateStatus(self, logger=None):
        """See `IBuilder`."""
        return updateBuilderStatus(self, logger)

    def cleanSlave(self):
        """See IBuilder."""
        return self.slave.clean()

    # XXX 2010-08-24 Julian bug=623281
    # This should not be a property!  It's masking a complicated query.
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
            return defer.fail(CannotResumeHost('Builder is not virtualized.'))

        if not self.vm_host:
            return defer.fail(CannotResumeHost('Undefined vm_host.'))

        logger = self._getSlaveScannerLogger()
        logger.info("Resuming %s (%s)" % (self.name, self.url))

        d = self.slave.resume()

        def got_resume_ok((stdout, stderr, returncode)):
            return stdout, stderr

        def got_resume_bad(failure):
            stdout, stderr, code = failure.value
            raise CannotResumeHost(
                "Resuming failed:\nOUT:\n%s\nERR:\n%s\n" % (stdout, stderr))

        return d.addCallback(got_resume_ok).addErrback(got_resume_bad)

    @cachedproperty
    def slave(self):
        """See IBuilder."""
        # A cached attribute is used to allow tests to replace
        # the slave object, which is usually an XMLRPC client, with a
        # stub object that removes the need to actually create a buildd
        # slave in various states - which can be hard to create.
        return BuilderSlave.makeBuilderSlave(self.url, self.vm_host)

    def setSlaveForTesting(self, proxy):
        """See IBuilder."""
        # XXX JeroenVermeulen 2011-11-09, bug=888010: Don't use this.
        # It's a trap.  See bug for details.
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
            d = self.resumeSlaveHost()
        else:
            d = defer.succeed(None)

        def ping_done(ignored):
            return self.current_build_behavior.dispatchBuildToSlave(
                build_queue_item.id, logger)

        def resume_done(ignored):
            # Before we try and contact the resumed slave, we're going
            # to send it a message.  This is to ensure it's accepting
            # packets from the outside world, because testing has shown
            # that the first packet will randomly fail for no apparent
            # reason.  This could be a quirk of the Xen guest, we're not
            # sure.  We also don't care about the result from this message,
            # just that it's sent, hence the "addBoth".
            # See bug 586359.
            if self.virtualized:
                d = self.slave.echo("ping")
            else:
                d = defer.succeed(None)
            d.addBoth(ping_done)
            return d

        d.addCallback(resume_done)
        return d

    def failBuilder(self, reason):
        """See IBuilder"""
        # XXX cprov 2007-04-17: ideally we should be able to notify the
        # the buildd-admins about FAILED builders. One alternative is to
        # make the buildd_cronscript (slave-scanner, in this case) to exit
        # with error, for those cases buildd-sequencer automatically sends
        # an email to admins with the script output.
        self.builderok = False
        self.failnotes = reason

    def getBuildRecords(self, build_state=None, name=None, arch_tag=None,
                        user=None, binary_only=True):
        """See IHasBuildRecords."""
        if binary_only:
            return getUtility(IBinaryPackageBuildSet).getBuildsForBuilder(
                self.id, build_state, name, arch_tag, user)
        else:
            if arch_tag is not None or name is not None:
                raise IncompatibleArguments(
                    "The 'arch_tag' and 'name' parameters can be used only "
                    "with binary_only=True.")
            return getUtility(IBuildFarmJobSet).getBuildsForBuilder(
                self, status=build_state, user=user)

    def slaveStatus(self):
        """See IBuilder."""
        d = self.slave.status()

        def got_status(status_sentence):
            status = {'builder_status': status_sentence[0]}

            # Extract detailed status and log information if present.
            # Although build_id is also easily extractable here, there is no
            # valid reason for anything to use it, so we exclude it.
            if status['builder_status'] == 'BuilderStatus.WAITING':
                status['build_status'] = status_sentence[1]
            else:
                if status['builder_status'] == 'BuilderStatus.BUILDING':
                    status['logtail'] = status_sentence[2]

            self.current_build_behavior.updateSlaveStatus(
                status_sentence, status)
            return status

        return d.addCallback(got_status)

    def slaveStatusSentence(self):
        """See IBuilder."""
        return self.slave.status()

    def verifySlaveBuildCookie(self, slave_build_id):
        """See `IBuilder`."""
        return self.current_build_behavior.verifySlaveBuildCookie(
            slave_build_id)

    def updateBuild(self, queueItem):
        """See `IBuilder`."""
        return self.current_build_behavior.updateBuild(queueItem)

    def transferSlaveFileToLibrarian(self, file_sha1, filename, private):
        """See IBuilder."""
        out_file_fd, out_file_name = tempfile.mkstemp(suffix=".buildlog")
        out_file = os.fdopen(out_file_fd, "r+")

        def got_file(ignored, filename, out_file, out_file_name):
            try:
                # If the requested file is the 'buildlog' compress it
                # using gzip before storing in Librarian.
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

                transaction.commit()
                with DatabaseTransactionPolicy(read_only=False):
                    library_file = getUtility(ILibraryFileAliasSet).create(
                        filename, bytes_written, out_file,
                        contentType=filenameToContentType(filename),
                        restricted=private)
                    transaction.commit()
            finally:
                # Remove the temporary file.  getFile() closes the file
                # object.
                os.remove(out_file_name)

            return library_file.id

        d = self.slave.getFile(file_sha1, out_file)
        d.addCallback(got_file, filename, out_file, out_file_name)
        return d

    def isAvailable(self):
        """See `IBuilder`."""
        if not self.builderok:
            return defer.succeed(False)
        d = self.slaveStatusSentence()

        def catch_fault(failure):
            failure.trap(xmlrpclib.Fault, socket.error)
            return False

        def check_available(status):
            return status[0] == BuilderStatus.IDLE
        return d.addCallbacks(check_available, catch_fault)

    def _getSlaveScannerLogger(self):
        """Return the logger instance from buildd-slave-scanner.py."""
        # XXX cprov 20071120: Ideally the Launchpad logging system
        # should be able to configure the root-logger instead of creating
        # a new object, then the logger lookups won't require the specific
        # name argument anymore. See bug 164203.
        logger = logging.getLogger('slave-scanner')
        return logger

    def acquireBuildCandidate(self):
        """Acquire a build candidate in an atomic fashion.

        When retrieving a candidate we need to mark it as building
        immediately so that it is not dispatched by another builder in the
        build manager.

        We can consider this to be atomic because although the build manager
        is a Twisted app and gives the appearance of doing lots of things at
        once, it's still single-threaded so no more than one builder scan
        can be in this code at the same time.

        If there's ever more than one build manager running at once, then
        this code will need some sort of mutex, or run in a single
        transaction.
        """
        candidate = self._findBuildCandidate()
        if candidate is not None:
            transaction.commit()
            with DatabaseTransactionPolicy(read_only=False):
                candidate.markAsBuilding(self)
                transaction.commit()
        return candidate

    def _findBuildCandidate(self):
        """Find a candidate job for dispatch to an idle buildd slave.

        The pending BuildQueue item with the highest score for this builder
        or None if no candidate is available.

        :return: A candidate job.
        """
        def qualify_subquery(job_type, sub_query):
            """Put the sub-query into a job type context."""
            qualified_query = """
                ((BuildQueue.job_type != %s) OR EXISTS(%%s))
            """ % sqlvalues(job_type)
            qualified_query %= sub_query
            return qualified_query

        logger = self._getSlaveScannerLogger()
        candidate = None

        general_query = """
            SELECT buildqueue.id FROM buildqueue, job
            WHERE
                buildqueue.job = job.id
                AND job.status = %s
                AND (
                    -- The processor values either match or the candidate
                    -- job is processor-independent.
                    buildqueue.processor = %s OR
                    buildqueue.processor IS NULL)
                AND (
                    -- The virtualized values either match or the candidate
                    -- job does not care about virtualization and the idle
                    -- builder *is* virtualized (the latter is a security
                    -- precaution preventing the execution of untrusted code
                    -- on native builders).
                    buildqueue.virtualized = %s OR
                    (buildqueue.virtualized IS NULL AND %s = TRUE))
                AND buildqueue.builder IS NULL
        """ % sqlvalues(
            JobStatus.WAITING, self.processor, self.virtualized,
            self.virtualized)
        order_clause = " ORDER BY buildqueue.lastscore DESC, buildqueue.id"

        extra_queries = []
        job_classes = specific_job_classes()
        for job_type, job_class in job_classes.iteritems():
            query = job_class.addCandidateSelectionCriteria(
                self.processor, self.virtualized)
            if query == '':
                # This job class does not need to refine candidate jobs
                # further.
                continue

            # The sub-query should only apply to jobs of the right type.
            extra_queries.append(qualify_subquery(job_type, query))
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
        # Using maybeDeferred ensures that any exceptions are also
        # wrapped up and caught later.
        d = defer.maybeDeferred(self.startBuild, candidate, logger)
        return d

    def handleTimeout(self, logger, error_message):
        """See IBuilder."""
        if self.virtualized:
            # Virtualized/PPA builder: attempt a reset.
            logger.warn(
                "Resetting builder: %s -- %s" % (self.url, error_message),
                exc_info=True)
            d = self.resumeSlaveHost()
            return d
        else:
            # XXX: This should really let the failure bubble up to the
            # scan() method that does the failure counting.
            # Mark builder as 'failed'.
            logger.warn(
                "Disabling builder: %s -- %s" % (self.url, error_message))
            self.failBuilder(error_message)
            return defer.succeed(None)

    def findAndStartJob(self, buildd_slave=None):
        """See IBuilder."""
        # XXX This method should be removed in favour of two separately
        # called methods that find and dispatch the job.  It will
        # require a lot of test fixing.
        logger = self._getSlaveScannerLogger()
        candidate = self.acquireBuildCandidate()

        if candidate is None:
            logger.debug("No build candidates available for builder.")
            return defer.succeed(None)

        if buildd_slave is not None:
            self.setSlaveForTesting(buildd_slave)

        d = self._dispatchBuildCandidate(candidate)
        return d.addCallback(lambda ignored: candidate)

    def getBuildQueue(self):
        """See `IBuilder`."""
        # Return a single BuildQueue for the builder provided it's
        # currently running a job.
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(
            BuildQueue,
            BuildQueue.job == Job.id,
            BuildQueue.builder == self.id,
            Job._status == JobStatus.RUNNING,
            Job.date_started != None).one()

    def getCurrentBuildFarmJob(self):
        """See `IBuilder`."""
        # Don't make this a property, it's masking a few queries.
        return self.currentjob.specific_job.build


class BuilderSet(object):
    """See IBuilderSet"""
    implements(IBuilderSet)

    def __init__(self):
        self.title = "The Launchpad build farm"

    def __iter__(self):
        return iter(Builder.select())

    def getByName(self, name):
        """See IBuilderSet."""
        try:
            return Builder.selectOneBy(name=name)
        except SQLObjectNotFound:
            raise NotFoundError(name)

    def __getitem__(self, name):
        return self.getByName(name)

    def new(self, processor, url, name, title, description, owner,
            active=True, virtualized=False, vm_host=None, manual=True):
        """See IBuilderSet."""
        return Builder(processor=processor, url=url, name=name, title=title,
                       description=description, owner=owner, active=active,
                       virtualized=virtualized, vm_host=vm_host,
                       _builderok=True, manual=manual)

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

    def getBuildQueueSizes(self):
        """See `IBuilderSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, SLAVE_FLAVOR)
        results = store.find((
            Count(),
            Sum(BuildQueue.estimated_duration),
            Processor,
            Coalesce(BuildQueue.virtualized, True)),
            Processor.id == BuildQueue.processorID,
            Job.id == BuildQueue.jobID,
            Job._status == JobStatus.WAITING).group_by(
                Processor, Coalesce(BuildQueue.virtualized, True))

        result_dict = {'virt': {}, 'nonvirt': {}}
        for size, duration, processor, virtualized in results:
            if virtualized is False:
                virt_str = 'nonvirt'
            else:
                virt_str = 'virt'
            result_dict[virt_str][processor.name] = (
                size, duration)

        return result_dict

    def getBuildersForQueue(self, processor, virtualized):
        """See `IBuilderSet`."""
        return Builder.selectBy(_builderok=True, processor=processor,
                                virtualized=virtualized)

# Copyright 2009-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'BuilderInteractor',
    ]

import logging
import socket
from urlparse import urlparse
import xmlrpclib

import transaction
from twisted.internet import defer
from twisted.web import xmlrpc
from twisted.web.client import downloadPage
from zope.component import getUtility
from zope.security.proxy import (
    isinstance as zope_isinstance,
    removeSecurityProxy,
    )

from lp.buildmaster.interfaces.builder import (
    BuildDaemonError,
    BuildSlaveFailure,
    CannotFetchFile,
    CannotResumeHost,
    CorruptBuildCookie,
    )
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior,
    )
from lp.services import encoding
from lp.services.config import config
from lp.services.job.interfaces.job import JobStatus
from lp.services.librarian.interfaces.client import ILibrarianClient
from lp.services.twistedsupport import cancel_on_timeout
from lp.services.twistedsupport.processmonitor import ProcessWithTimeout
from lp.services.webapp import urlappend


class QuietQueryFactory(xmlrpc._QueryFactory):
    """XMLRPC client factory that doesn't splatter the log with junk."""
    noisy = False


class BuilderSlave(object):
    """Add in a few useful methods for the XMLRPC slave.

    :ivar url: The URL of the actual builder. The XML-RPC resource and
        the filecache live beneath this.
    """

    # WARNING: If you change the API for this, you should also change the APIs
    # of the mocks in soyuzbuilderhelpers to match. Otherwise, you will have
    # many false positives in your test run and will most likely break
    # production.

    def __init__(self, proxy, builder_url, vm_host, timeout, reactor):
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
        self.timeout = timeout
        self.reactor = reactor

    @classmethod
    def makeBuilderSlave(cls, builder_url, vm_host, timeout, reactor=None,
                         proxy=None):
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
            server_proxy = xmlrpc.Proxy(
                rpc_url, allowNone=True, connectTimeout=timeout)
            server_proxy.queryFactory = QuietQueryFactory
        else:
            server_proxy = proxy
        return cls(server_proxy, builder_url, vm_host, timeout, reactor)

    def _with_timeout(self, d):
        return cancel_on_timeout(d, self.timeout, self.reactor)

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
        url_components = urlparse(self.url)
        buildd_name = url_components.hostname.split('.')[0]
        resume_command = config.builddmaster.vm_resume_command % {
            'vm_host': self._vm_host,
            'buildd_name': buildd_name}
        # Twisted API requires string but the configuration provides unicode.
        resume_argv = [
            term.encode('utf-8') for term in resume_command.split()]
        d = defer.Deferred()
        p = ProcessWithTimeout(d, self.timeout, clock=clock)
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


class BuilderInteractor(object):

    _cached_build_behavior = None
    _cached_currentjob = None

    _cached_slave = None
    _cached_slave_attrs = None

    # Tests can override _current_build_behavior and slave.
    _override_behavior = None
    _override_slave = None

    def __init__(self, builder, override_slave=None, override_behavior=None):
        self.builder = builder
        self._override_slave = override_slave
        self._override_behavior = override_behavior

    @property
    def slave(self):
        """See IBuilder."""
        if self._override_slave is not None:
            return self._override_slave
        # The slave cache is invalidated when the builder's URL, VM host
        # or virtualisation change.
        new_slave_attrs = (
            self.builder.url, self.builder.vm_host, self.builder.virtualized)
        if self._cached_slave_attrs != new_slave_attrs:
            if self.builder.virtualized:
                timeout = config.builddmaster.virtualized_socket_timeout
            else:
                timeout = config.builddmaster.socket_timeout
            self._cached_slave = BuilderSlave.makeBuilderSlave(
                self.builder.url, self.builder.vm_host, timeout)
            self._cached_slave_attrs = new_slave_attrs
        return self._cached_slave

    @property
    def _current_build_behavior(self):
        """Return the current build behavior."""
        if self._override_behavior is not None:
            return self._override_behavior
        # The _current_build_behavior cache is invalidated when
        # builder.currentjob changes.
        currentjob = self.builder.currentjob
        if currentjob is None:
            self._cached_build_behavior = None
            self._cached_currentjob = None
        elif currentjob != self._cached_currentjob:
            self._cached_build_behavior = IBuildFarmJobBehavior(
                currentjob.specific_job)
            self._cached_build_behavior.setBuilderInteractor(self)
            self._cached_currentjob = currentjob
        return self._cached_build_behavior

    def slaveStatus(self):
        """Get the slave status for this builder.

        :return: A Deferred which fires when the slave dialog is complete.
            Its value is a dict containing at least builder_status, but
            potentially other values included by the current build
            behavior.
        """
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
            return (status_sentence, status)

        return d.addCallback(got_status)

    def isAvailable(self):
        """Whether or not a builder is available for building new jobs.

        :return: A Deferred that fires with True or False, depending on
            whether the builder is available or not.
        """
        if not self.builder.builderok:
            return defer.succeed(False)
        d = self.slave.status()

        def catch_fault(failure):
            failure.trap(xmlrpclib.Fault, socket.error)
            return False

        def check_available(status):
            return status[0] == 'BuilderStatus.IDLE'
        return d.addCallbacks(check_available, catch_fault)

    def verifySlaveBuildCookie(self, slave_build_cookie):
        """See `IBuildFarmJobBehavior`."""
        if self._current_build_behavior is None:
            raise CorruptBuildCookie('No job assigned to builder')
        good_cookie = self._current_build_behavior.generateSlaveBuildCookie()
        if slave_build_cookie != good_cookie:
            raise CorruptBuildCookie("Invalid slave build cookie.")

    def rescueIfLost(self, logger=None):
        """Reset the slave if its job information doesn't match the DB.

        This checks the build ID reported in the slave status against the
        database. If it isn't building what we think it should be, the current
        build will be aborted and the slave cleaned in preparation for a new
        task. The decision about the slave's correctness is left up to
        `IBuildFarmJobBehavior.verifySlaveBuildCookie`.

        :return: A Deferred that fires when the dialog with the slave is
            finished.  It does not have a return value.
        """
        # 'ident_position' dict relates the position of the job identifier
        # token in the sentence received from status(), according to the
        # two statuses we care about. See lp:launchpad-buildd
        # for further information about sentence format.
        ident_position = {
            'BuilderStatus.BUILDING': 1,
            'BuilderStatus.WAITING': 2
            }

        d = self.slave.status()

        def got_status(status_sentence):
            """After we get the status, clean if we have to.

            Always return status_sentence.
            """
            # Isolate the BuilderStatus string, always the first token in
            # BuilderSlave.status().
            status = status_sentence[0]

            # If the cookie test below fails, it will request an abort of the
            # builder.  This will leave the builder in the aborted state and
            # with no assigned job, and we should now "clean" the slave which
            # will reset its state back to IDLE, ready to accept new builds.
            # This situation is usually caused by a temporary loss of
            # communications with the slave and the build manager had to reset
            # the job.
            if (status == 'BuilderStatus.ABORTED'
                    and self.builder.currentjob is None):
                if not self.builder.virtualized:
                    # We can't reset non-virtual builders reliably as the
                    # abort() function doesn't kill the actual build job,
                    # only the sbuild process!  All we can do here is fail
                    # the builder with a message indicating the problem and
                    # wait for an admin to reboot it.
                    self.builder.failBuilder(
                        "Non-virtual builder in ABORTED state, requires admin "
                        "to restart")
                    return "dummy status"
                if logger is not None:
                    logger.info(
                        "Builder '%s' being cleaned up from ABORTED" %
                        (self.builder.name,))
                d = self.cleanSlave()
                return d.addCallback(lambda ignored: status_sentence)
            else:
                return status_sentence

        def rescue_slave(status_sentence):
            # If slave is not building nor waiting, it's not in need of
            # rescuing.
            status = status_sentence[0]
            if status not in ident_position.keys():
                return
            slave_build_id = status_sentence[ident_position[status]]
            try:
                self.verifySlaveBuildCookie(slave_build_id)
            except CorruptBuildCookie as reason:
                if status == 'BuilderStatus.WAITING':
                    d = self.cleanSlave()
                else:
                    d = self.requestAbort()

                def log_rescue(ignored):
                    if logger:
                        logger.info(
                            "Builder '%s' rescued from '%s': '%s'" %
                            (self.builder.name, slave_build_id, reason))
                return d.addCallback(log_rescue)

        d.addCallback(got_status)
        d.addCallback(rescue_slave)
        return d

    def updateStatus(self, logger=None):
        """Update the builder's status by probing it.

        :return: A Deferred that fires when the dialog with the slave is
            finished.  It does not have a return value.
        """
        if logger:
            logger.debug('Checking %s' % self.builder.name)

        return self.rescueIfLost(logger)

    def cleanSlave(self):
        """Clean any temporary files from the slave.

        :return: A Deferred that fires when the dialog with the slave is
            finished.  It does not have a return value.
        """
        return self.slave.clean()

    def requestAbort(self):
        """Ask that a build be aborted.

        This takes place asynchronously: Actually killing everything running
        can take some time so the slave status should be queried again to
        detect when the abort has taken effect. (Look for status ABORTED).

        :return: A Deferred that fires when the dialog with the slave is
            finished.  It does not have a return value.
        """
        return self.slave.abort()

    def resumeSlaveHost(self):
        """Resume the slave host to a known good condition.

        Issues 'builddmaster.vm_resume_command' specified in the configuration
        to resume the slave.

        :raises: CannotResumeHost: if builder is not virtual or if the
            configuration command has failed.

        :return: A Deferred that fires when the resume operation finishes,
            whose value is a (stdout, stderr) tuple for success, or a Failure
            whose value is a CannotResumeHost exception.
        """
        if not self.builder.virtualized:
            return defer.fail(CannotResumeHost('Builder is not virtualized.'))

        if not self.builder.vm_host:
            return defer.fail(CannotResumeHost('Undefined vm_host.'))

        logger = self._getSlaveScannerLogger()
        logger.info("Resuming %s (%s)" % (self.builder.name, self.builder.url))

        d = self.slave.resume()

        def got_resume_ok((stdout, stderr, returncode)):
            return stdout, stderr

        def got_resume_bad(failure):
            stdout, stderr, code = failure.value
            raise CannotResumeHost(
                "Resuming failed:\nOUT:\n%s\nERR:\n%s\n" % (stdout, stderr))

        return d.addCallback(got_resume_ok).addErrback(got_resume_bad)

    def _startBuild(self, build_queue_item, logger):
        """Start a build on this builder.

        :param build_queue_item: A BuildQueueItem to build.
        :param logger: A logger to be used to log diagnostic information.

        :return: A Deferred that fires after the dispatch has completed whose
            value is None, or a Failure that contains an exception
            explaining what went wrong.
        """
        needed_bfjb = type(removeSecurityProxy(
            IBuildFarmJobBehavior(build_queue_item.specific_job)))
        if not zope_isinstance(self._current_build_behavior, needed_bfjb):
            raise AssertionError(
                "Inappropriate IBuildFarmJobBehavior: %r is not a %r" %
                (self._current_build_behavior, needed_bfjb))
        self._current_build_behavior.logStartBuild(logger)

        # Make sure the request is valid; an exception is raised if it's not.
        self._current_build_behavior.verifyBuildRequest(logger)

        # Set the build behavior depending on the provided build queue item.
        if not self.builder.builderok:
            raise BuildDaemonError(
                "Attempted to start a build on a known-bad builder.")

        # If we are building a virtual build, resume the virtual machine.
        if self.builder.virtualized:
            d = self.resumeSlaveHost()
        else:
            d = defer.succeed(None)

        def ping_done(ignored):
            return self._current_build_behavior.dispatchBuildToSlave(
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
            if self.builder.virtualized:
                d = self.slave.echo("ping")
            else:
                d = defer.succeed(None)
            d.addBoth(ping_done)
            return d

        d.addCallback(resume_done)
        return d

    def resetOrFail(self, logger, exception):
        """Handle "confirmed" build slave failures.

        Call this when there have been multiple failures that are not just
        the fault of failing jobs, or when the builder has entered an
        ABORTED state without having been asked to do so.

        In case of a virtualized/PPA buildd slave an attempt will be made
        to reset it (using `resumeSlaveHost`).

        Conversely, a non-virtualized buildd slave will be (marked as)
        failed straightaway (using `failBuilder`).

        :param logger: The logger object to be used for logging.
        :param exception: An exception to be used for logging.
        :return: A Deferred that fires after the virtual slave was resumed
            or immediately if it's a non-virtual slave.
        """
        error_message = str(exception)
        if self.builder.virtualized:
            # Virtualized/PPA builder: attempt a reset, unless the failure
            # was itself a failure to reset.  (In that case, the slave
            # scanner will try again until we reach the failure threshold.)
            if not isinstance(exception, CannotResumeHost):
                logger.warn(
                    "Resetting builder: %s -- %s" % (
                        self.builder.url, error_message),
                    exc_info=True)
                return self.resumeSlaveHost()
        else:
            # XXX: This should really let the failure bubble up to the
            # scan() method that does the failure counting.
            # Mark builder as 'failed'.
            logger.warn(
                "Disabling builder: %s -- %s" % (
                    self.builder.url, error_message))
            self.builder.failBuilder(error_message)
        return defer.succeed(None)

    def findAndStartJob(self):
        """Find a job to run and send it to the buildd slave.

        :return: A Deferred whose value is the `IBuildQueue` instance
            found or None if no job was found.
        """
        # XXX This method should be removed in favour of two separately
        # called methods that find and dispatch the job.  It will
        # require a lot of test fixing.
        logger = self._getSlaveScannerLogger()
        candidate = self.builder.acquireBuildCandidate()

        if candidate is None:
            logger.debug("No build candidates available for builder.")
            return defer.succeed(None)

        # Using maybeDeferred ensures that any exceptions are also
        # wrapped up and caught later.
        d = defer.maybeDeferred(self._startBuild, candidate, logger)
        return d.addCallback(lambda ignored: candidate)

    def updateBuild(self, queueItem):
        """Verify the current build job status.

        Perform the required actions for each state.

        :return: A Deferred that fires when the slave dialog is finished.
        """
        logger = logging.getLogger('slave-scanner')

        d = self.slaveStatus()

        def got_failure(failure):
            failure.trap(xmlrpclib.Fault, socket.error)
            info = failure.value
            info = ("Could not contact the builder %s, caught a (%s)"
                    % (queueItem.builder.url, info))
            raise BuildSlaveFailure(info)

        def got_status(statuses):
            builder_status_handlers = {
                'BuilderStatus.IDLE': self.updateBuild_IDLE,
                'BuilderStatus.BUILDING': self.updateBuild_BUILDING,
                'BuilderStatus.ABORTING': self.updateBuild_ABORTING,
                'BuilderStatus.ABORTED': self.updateBuild_ABORTED,
                'BuilderStatus.WAITING': self.updateBuild_WAITING,
                }
            status_sentence, status_dict = statuses
            builder_status = status_dict['builder_status']
            if builder_status not in builder_status_handlers:
                logger.critical(
                    "Builder on %s returned unknown status %s, failing it"
                    % (self.builder.url, builder_status))
                self.builder.failBuilder(
                    "Unknown status code (%s) returned from status() probe."
                    % builder_status)
                # XXX: This will leave the build and job in a bad state, but
                # should never be possible, since our builder statuses are
                # known.
                queueItem._builder = None
                queueItem.setDateStarted(None)
                transaction.commit()
                return

            method = builder_status_handlers[builder_status]
            return defer.maybeDeferred(
                method, queueItem, status_sentence, status_dict, logger)

        d.addErrback(got_failure)
        d.addCallback(got_status)
        return d

    def updateBuild_IDLE(self, queueItem, status_sentence, status_dict,
                         logger):
        """Somehow the builder forgot about the build job.

        Log this and reset the record.
        """
        logger.warn(
            "Builder %s forgot about buildqueue %d -- resetting buildqueue "
            "record" % (queueItem.builder.url, queueItem.id))
        queueItem.reset()
        transaction.commit()

    def updateBuild_BUILDING(self, queueItem, status_sentence, status_dict,
                             logger):
        """Build still building, collect the logtail"""
        if queueItem.job.status != JobStatus.RUNNING:
            queueItem.job.start()
        queueItem.logtail = encoding.guess(str(status_dict.get('logtail')))
        transaction.commit()

    def updateBuild_ABORTING(self, queueItem, status_sentence, status_dict,
                             logger):
        """Build was ABORTED.

        Master-side should wait until the slave finish the process correctly.
        """
        queueItem.logtail = "Waiting for slave process to be terminated"
        transaction.commit()

    def updateBuild_ABORTED(self, queueItem, status_sentence, status_dict,
                            logger):
        """ABORTING process has successfully terminated.

        Clean the builder for another jobs.
        """
        d = self.cleanSlave()

        def got_cleaned(ignored):
            queueItem.builder = None
            if queueItem.job.status != JobStatus.FAILED:
                queueItem.job.fail()
            queueItem.specific_job.jobAborted()
            transaction.commit()
        return d.addCallback(got_cleaned)

    def extractBuildStatus(self, status_dict):
        """Read build status name.

        :param status_dict: build status dict as passed to the
            updateBuild_* methods.
        :return: the unqualified status name, e.g. "OK".
        """
        status_string = status_dict['build_status']
        lead_string = 'BuildStatus.'
        assert status_string.startswith(lead_string), (
            "Malformed status string: '%s'" % status_string)

        return status_string[len(lead_string):]

    def updateBuild_WAITING(self, queueItem, status_sentence, status_dict,
                            logger):
        """Perform the actions needed for a slave in a WAITING state

        Buildslave can be WAITING in five situations:

        * Build has failed, no filemap is received (PACKAGEFAIL, DEPFAIL,
                                                    CHROOTFAIL, BUILDERFAIL,
                                                    ABORTED)

        * Build has been built successfully (BuildStatus.OK), in this case
          we have a 'filemap', so we can retrieve those files and store in
          Librarian with getFileFromSlave() and then pass the binaries to
          the uploader for processing.
        """
        self._current_build_behavior.updateSlaveStatus(
            status_sentence, status_dict)
        d = self._current_build_behavior.handleStatus(
            self.extractBuildStatus(status_dict),
            getUtility(ILibrarianClient), status_dict)
        return d

    def _getSlaveScannerLogger(self):
        """Return the logger instance from buildd-slave-scanner.py."""
        # XXX cprov 20071120: Ideally the Launchpad logging system
        # should be able to configure the root-logger instead of creating
        # a new object, then the logger lookups won't require the specific
        # name argument anymore. See bug 164203.
        logger = logging.getLogger('slave-scanner')
        return logger

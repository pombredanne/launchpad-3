#!/usr/bin/env python
"""Soyuz buildd slave manager logic."""

import logging

from twisted.application import service
from twisted.internet import reactor, utils, defer
from twisted.internet.threads import deferToThread
from twisted.protocols.policies import TimeoutMixin
from twisted.web.xmlrpc import Proxy, _QueryFactory, QueryProtocol

from zope.component import getUtility
from zope.security.management import endInteraction, newInteraction

from canonical.config import config
from canonical.launchpad.interfaces.build import BuildStatus
from canonical.launchpad.interfaces.builder import IBuilderSet
from canonical.launchpad.webapp import urlappend
from canonical.librarian.db import write_transaction


class FakeZTM:
    """Fake transaction manager."""
    def commit(self):
        pass
    def abort(self):
        pass


class QueryWithTimeoutProtocol(QueryProtocol, TimeoutMixin):
    """XMLRPC query protocol with a configurable timeout."""

    def connectionMade(self):
        QueryProtocol.connectionMade(self)
        self.setTimeout(config.builddmaster.socket_timeout)


class QueryFactoryWithTimeout(_QueryFactory):
    """XMLRPC client facory with timeout support."""
    protocol = QueryWithTimeoutProtocol


class RecordingSlave:
    """An RPC proxy for buildd slaves that records instructions to the latter.

    The idea here is to merely record the instructions that the slave-scanner
    issues to the buildd slaves and "replay" them a bit later in asynchronous
    and parallel fashion.

    By dealing with a number of buildd slaves in parallel we remove *the*
    major slave-scanner throughput issue while avoiding large-scale changes to
    its code base.
    """
    def __init__(self, name, url):
        self.name = name
        self.url = url
        self.resume = False
        self.resume_argv = None
        self.calls = []

    def __repr__(self):
        return '<%s:%s>' % (self.name, self.url)

    def ensurepresent(self, *args):
        self.calls.append(('ensurepresent', args))
        return (True, 'Download')

    def build(self, *args):
        self.calls.append(('build', args))
        return ('BuilderStatus.BUILDING', args[0])

    def resumeHost(self, logger, resume_argv):
        """Record the request to initialize a builder to a known state.

        The supplied resume command will be run in a deferred and parallel
        fashion in order to increase the slave-scanner throughput.
        For now we merely record it.

        :param logger: the logger to use
        :param resume_argv: the resume command to run (sequence of strings)

        :return: a (stdout, stderr, subprocess exitcode) triple
        """
        self.resume = True
        logger.debug("Recording slave reset request for %s", self.url)
        self.resume_argv = resume_argv
        return ('', '', 0)

    def resumeSlaveHost(self):
        """Initialize a virtual builder to a known state.

        The recorded resume command is run in a subprocess in order to reset a
        slave to a known state. This method will only be invoked for virtual
        slaves.

        :return: a deferred
        """
        d = utils.getProcessOutputAndValue(
            str(self.resume_argv[0]), [str(u) for u in self.resume_argv[1:]])
        return d


class BaseBuilderRequest:
    """Base class for *BuilderRequest variations.

    This calls
    """

    def __init__(self, slave, info=None):
        self.slave = slave
        self.info = info

    def _cleanJob(self, job):
        """Clean up in case of builder reset or dispatch failure."""
        if job is not None:
            job.build.buildstate = BuildStatus.NEEDSBUILD
            job.builder = None
            job.buildstart = None
            job.logtail = None

    def ___call__(self):
        raise NotImplementedError(
            "Call sites must define a evaluation method.")


class FailBuilderRequest(BaseBuilderRequest):
    """Clean up in case we failed to dispatch to a builder."""

    def __repr__(self):
        return  '%r failure (%s)' % (self.slave, self.info)

    @write_transaction
    def __call__(self):
        builder = getUtility(IBuilderSet)[self.slave.name]
        builder.failbuilder(self.info)
        self._cleanJob(builder.currentjob)


class ResetBuilderRequest(BaseBuilderRequest):
    """Clean up in case a builder could not be reset."""

    def __repr__(self):
        return  '%r reset' % self.slave

    @write_transaction
    def __call__(self):
        builder = getUtility(IBuilderSet)[self.slave.name]
        self._cleanJob(builder.currentjob)


class BuilddManager(service.Service):

    reset_request = ResetBuilderRequest
    fail_request = FailBuilderRequest

    def __init__(self):
        self._deferreds = []
        self.remaining_slaves = []

        level = logging.INFO
        logger = logging.getLogger('slave-scanner')
        logger.setLevel(level)
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(logging.Formatter('%(levelname)s %(message)s'))
        logger.addHandler(ch)
        self.logger = logger

    def startService(self):
        self.logger.info('Starting scanning cycle.')
        d = deferToThread(self.scan)
        d.addCallback(self.resumeAndDispatch)
        d.addErrback(self.scanFailed)

    def scanFailed(self, error):
        self.logger.info(
            'Scanning failed with: %s' % error.getErrorMessage())
        #traceback_lines = error.getBriefTraceback().splitlines()
        #for line in traceback_lines:
        #    self.logger.info('\t%s' % line)
        self.finishCycle()

    def nextCycle(self):
        """Stops the reactor.

        It is usually overridden for tests.
        """
        self.logger.info('Next cycle in 5 seconds.')
        reactor.callLater(5, self.startService) #reactor.stop()

    def slaveDone(self, slave):
        """Mark slave as done for this cycle."""
        self.logger.info('%r marked as done.' % slave)
        self.remaining_slaves.remove(slave)
        if len(self.remaining_slaves) == 0:
            self.finishCycle()

    def finishCycle(self, r=None):
        """Finishes a slave-scanning cycle.

        Once all the active events were executed:

         * Evaluate pending builder update requests;
         * Clean the list of active events;
         * Call `gameOver`.
        """
        def done(results):
            self.logger.info('Scanning cycle finished.')
            requests = [
                request for status, request in results
                if isinstance(request, BaseBuilderRequest)]
            for request in requests:
                self.logger.info('%r' % request)
                request()

            self._deferreds = []
            self.nextCycle()
            return results

        self.logger.info('Finishing scanning cycle.')
        dl = defer.DeferredList(self._deferreds, consumeErrors=True)
        dl.addBoth(done)
        return dl

    @write_transaction
    def scan(self):
        """Scan all builders and "dispatch" build jobs to the idle ones.

        All builders are polled for status and any required post-processing
        actions are performed.

        Subsequently, build job candidates are selected and assigned to the
        idle builders. The necessary build job assignment actions are not
        carried out directly though but merely memorized by the recording
        build slaves.

        In a second stage (see resumeAndDispatch()) each of the latter will be
        handled in an asynchronous and parallel fashion.
        """
        recording_slaves = []

        newInteraction()
        builder_set = getUtility(IBuilderSet)
        builder_set.pollBuilders(self.logger, FakeZTM())

        for builder in builder_set:
            # XXX cprov 2007-11-09: we don't support manual dispatching
            # yet. Once we support it this clause should be removed.
            if builder.manual:
                self.logger.debug('Builder is in manual state, ignored.')
                continue

            if not builder.is_available:
                self.logger.debug('Builder is not available, ignored.')
                continue

            candidate = builder.findBuildCandidate()
            if candidate is None:
                self.logger.debug("No build candidates available for builder.")
                continue

            slave = RecordingSlave(builder.name, builder.url)
            builder.setSlaveForTesting(slave)

            builder.dispatchBuildCandidate(candidate)
            recording_slaves.append(slave)

        endInteraction()
        return recording_slaves

    def checkResume(self, response, slave):
        """Verify the results of a slave resume procedure.

        If it failed returns a correspoding `ResetBuilderRequest` database
        update request.
        """
        out, err, code = response
        if code == 0:
            return
        self.slaveDone(slave)
        return self.reset_request(slave)

    def checkDispatch(self, response, slave):
        """Verify the results of a slave  xmlrpc calls.

        If it failed returns a correspoding `FailBuilderRequest` database
        update request. Otherwise dispatch the next call if there are any
        and return None.
        """
        status, info = response
        if status:
            self._mayDispatch(slave)
            return
        self.slaveDone(slave)
        return self.fail_request(slave, info)

    def resumeAndDispatch(self, recording_slaves):
        """Dispatch existing resume procedure calls and chain dispatching.

        See `RecordingSlave.resumeSlaveHost` for more details.
        """
        self.logger.info('Resuming slaves: %s' % recording_slaves)
        self.remaining_slaves = recording_slaves
        if len(self.remaining_slaves) == 0:
            self.finishCycle()

        for slave in recording_slaves:
            if slave.resume:
                # The buildd slave needs to be reset before we can dispatch
                # builds to it.
                d = slave.resumeSlaveHost()
                d.addCallback(self.checkResume, slave)
            else:
                # Buildd slave is clean, we can dispatch a build to it
                # straightaway.
                d = defer.succeed(None)
            d.addCallback(self.dispatchBuild, slave)
            # Store the active deferred.
            self._deferreds.append(d)

    def dispatchBuild(self, resume_result, slave):
        """Start dispatching a build to a slave.

        If the previous task in chain (slave resuming) has failed it will
        receive a `ResetBuilderRequest` instance as 'resume_result' and
        will immeadiately return that so the subsequent callback can collect
        it.

        if the slave resuming succeeed, it starts the XMLRPC dialog. See
        `_mayDispatch` for more information.
        """
        self.logger.info('Dispatching: %s' % slave)
        if resume_result is not None:
            self.slaveDone(slave)
            return resume_result
        self._mayDispatch(slave)

    def _getProxyForSlave(self, slave):
        """Return a twisted.web.xmlrpc.Proxy for the buildd slave.

        Uses a protocol with timeout support, See QueryFactoryWithTimeout.
        """
        proxy = Proxy(str(urlappend(slave.url, 'rpc')))
        proxy.queryFactory = QueryFactoryWithTimeout
        return proxy

    def _mayDispatch(self, slave):
        """Dispatch the next XMLRPC for the given slave.

        If there are not return None, Otherwise it will fetch a new XMLRPC
        proxy, dispatch the call and set `checkDispatch` as callback
        """
        if len(slave.calls) == 0:
            self.slaveDone(slave)
            return

        # Get an XMPRPC proxy for the buildd slave.
        proxy = self._getProxyForSlave(slave)
        method, args = slave.calls.pop(0)
        d = proxy.callRemote(method, *args)
        d.addCallback(self.checkDispatch, slave)

        # Store another active event.
        self._deferreds.append(d)
        self.logger.info('%s -> %s(%s)' % (slave, method, args))

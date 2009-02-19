#!/usr/bin/env python
"""Soyuz buildd slave manager logic."""

import logging

from twisted.application import service
from twisted.internet import reactor, utils, defer
from twisted.internet.threads import deferToThread
from twisted.web.xmlrpc import Proxy

from zope.component import getUtility
from zope.security.management import newInteraction

from canonical.launchpad.interfaces.build import BuildStatus
from canonical.launchpad.interfaces.builder import IBuilderSet
from canonical.launchpad.webapp import urlappend
from canonical.librarian.db import write_transaction


class FakeZTM:
    def commit(self):
        pass
    def abort(self):
        pass


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
        print('RS: ensurepresent()')
        self.calls.append(('ensurepresent', args))
        return (True, 'Download')

    def build(self, *args):
        print('RS: build()')
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
        print('RS: resumeHost()')
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
        print('RS: resumeSlaveHost()')
        d = utils.getProcessOutputAndValue(
            self.resume_argv[0], self.resume_argv[1:])
        return d


class BuilddProxy:

    @write_transaction
    def scanAllBuilders(self):
        recording_slaves = []

        level = logging.DEBUG
        logger = logging.getLogger('slave-scanner')
        logger.setLevel(level)
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(logging.Formatter('%(levelname)s %(message)s'))
        logger.addHandler(ch)

        newInteraction()

        builder_set = getUtility(IBuilderSet)
        builder_set.pollBuilders(logger, FakeZTM())

        for builder in builder_set:
            # XXX cprov 2007-11-09: we don't support manual dispatching
            # yet. Once we support it this clause should be removed.
            if builder.manual:
                logger.warn('Builder is in manual state, ignored.')
                continue

            if not builder.is_available:
                logger.warn('Builder is not available, ignored.')
                continue

            candidate = builder.findBuildCandidate()
            if candidate is None:
                logger.debug("No build candidates available for builder.")
                continue

            slave = RecordingSlave(builder.name, builder.url)
            builder.setSlaveForTesting(slave)

            builder.dispatchBuildCandidate(candidate)
            recording_slaves.append(slave)

        return recording_slaves

    def _cleanJob(self, job):
        if job is not None:
            job.build.buildstate = BuildStatus.NEEDSBUILD
            job.builder = None
            job.buildstart = None
            job.logtail = None

    @write_transaction
    def resetBuilder(self, name):
        newInteraction()
        print 'RESET'
        builder = getUtility(IBuilderSet)[name]
        self._cleanJob(builder.currentjob)

    @write_transaction
    def dispatchFail(self, error, name):
        newInteraction()
        print 'ERROR'
        builder = getUtility(IBuilderSet)[name]
        builder.failbuilder(error)
        self._cleanJob(builder.currentjob)


class BuilddManager(service.Service):

    def __init__(self):
        self.buildd_proxy = BuilddProxy()
        self.runningJobs = 0

    def startService(self):
        deferred = deferToThread(self.scan)
        deferred.addCallback(self.resumeAndDispatch)

    def scan(self):
        return self.buildd_proxy.scanAllBuilders()

    def checkResume(self, response, name):
        out, err, code = response
        if code != 0:
            print 'RESUME FAIL', name, response
            self.buildd_proxy.resetBuilder(name)

    def resumeAndDispatch(self, recording_slaves):
        print('BM: resumeAndDispatch()')
        print('RESUME/DISPATCH: %s' % recording_slaves)

        for slave in recording_slaves:
            self.runningJobs += 1
            if slave.resume:
                print('RESUME: yes')
                # The buildd slave needs to be reset before we can dispatch
                # builds to it.
                d = slave.resumeSlaveHost()
                d.addCallback(self.checkResume, slave.name)
            else:
                print('RESUME: no')
                # Buildd slave is clean, we can dispatch a build to it
                # straightaway.
                d = defer.maybeDeferred(lambda: True)
            d.addCallback(self.dispatchBuild, slave)
            d.addBoth(self.stopWhenDone)

    def dispatchBuild(self, resume_ok, slave):
        print('BM: dispatchBuild()')
        print('DISPATCH: %s/%s' % (resume_ok, slave))
        # Stop right here if the buildd slave could not be reset.
        if not resume_ok:
            return

        proxy = Proxy(str(urlappend(slave.url, 'rpc')))
        for method, args in slave.calls:
            self.runningJobs += 1
            d = proxy.callRemote(method, *args)
            d.addCallback(self.checkDispatch, slave.name)
            d.addErrback(self.dispatchFail, slave.name)

    def stopWhenDone(self, result):
        print('STOP: %s' % self.runningJobs)
        self.runningJobs -= 1
        if self.runningJobs <= 0:
            reactor.stop()

    def checkDispatch(self, response, name):
        status, info = response
        if not status:
            print 'DISPATCH FAIL', name, response
            self.buildd_proxy.resetBuilder(name)


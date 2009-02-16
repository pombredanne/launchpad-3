#!/usr/bin/env python
"""Soyuz buildd slave manager logic."""

import logging

from twisted.application import service
from twisted.internet import reactor, utils
from twisted.internet.threads import deferToThread
from twisted.web.xmlrpc import Proxy

from zope.component import getUtility
from zope.security.management import newInteraction

from canonical.config import config
from canonical.launchpad.interfaces.build import BuildStatus
from canonical.launchpad.interfaces.builder import IBuilderSet
from canonical.launchpad.webapp import urlappend
from canonical.librarian.db import read_transaction, write_transaction


class FakeZTM:

    def commit(self):
        pass

    def abort(self):
        pass


class RecordingSlave:

    def __init__(self, name, url, vm_host, virtualized):
        self.name = name
        self.url = url
        self.vm_host = vm_host
        self.virtualized = virtualized

        self.resume = False

        self.calls = []

    def __repr__(self):
        return '<%s:%s>' % (self.name, self.url)

    def ensurepresent(self, *args):
        self.calls.append(('ensurepresent', args))
        return (True, 'Download')

    def build(self, *args):
        self.calls.append(('build', args))
        return ('BuilderStatus.BUILDING', args[0])

    def resumeHost(self):
        resume_command = config.builddmaster.vm_resume_command % {
            'vm_host': self.vm_host}
        resume_argv = [str(part) for part in resume_command.split()]
        d = utils.getProcessOutputAndValue(resume_argv[0], resume_argv[1:])
        return d


class BuilddManager(service.Service):

    def __init__(self):
        level = logging.DEBUG

        logger = logging.getLogger('slave-scanner')
        logger.setLevel(level)
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(logging.Formatter('%(levelname)s %(message)s'))
        logger.addHandler(ch)

    def startService(self):
        deferred = deferToThread(self.scanAllBuilders)
        deferred.addCallback(self.resume)

    @write_transaction
    def scanAllBuilders(self):
        recording_slaves = []
        logger = logging.getLogger('slave-scanner')

        newInteraction()

        builder_set = getUtility(IBuilderSet)
        builder_set.pollBuilders(logger, FakeZTM())

        for builder in builder_set:
            # XXX cprov 2007-11-09: we don't support manual dispatching
            # yet. Once we support it this clause should be removed.
            if builder.manual:
                logger.warn('builder is in manual state. Ignored.')
                continue

            if not builder.is_available:
                logger.warn('builder is not available. Ignored.')
                continue

            candidate = builder.findBuildCandidate()
            if candidate is None:
                logger.debug(
                    "No candidates available for builder.")
                continue

            slave = RecordingSlave(
                builder.name, builder.url, builder.vm_host,
                builder.virtualized)

            def localResume():
                slave.resume = True

            from zope.security.proxy import removeSecurityProxy
            naked_builder = removeSecurityProxy(builder)
            naked_builder.resumeSlaveHost = localResume
            builder.setSlaveForTesting(slave)

            builder.dispatchBuildCandidate(candidate)
            recording_slaves.append(slave)

        return recording_slaves

    def checkResume(self, response, name):
        out, err, code = response
        if code != 0:
            print 'RESUME FAIL', name, response
            self.resetBuilder(name)

    def resume(self, recording_slaves):
        print 'RESUMING:', recording_slaves

        self.rounds = 0
        def check_rounds(r):
            self.rounds -= 1
            if self.rounds == 0:
                self.dispatch(recording_slaves)

        for slave in recording_slaves:
            if slave.resume:
                self.rounds += 1
                d = slave.resumeHost()
                d.addCallback(self.checkResume, slave.name)
                d.addBoth(check_rounds)

        if self.rounds == 0:
            reactor.stop()

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

    def checkDispatch(self, response, name):
        status, info = response
        if not status:
            print 'DISPATCH FAIL', name, response
            self.resetBuilder(name)

    @write_transaction
    def dispatchFail(self, error, name):
        newInteraction()
        print 'ERROR'
        builder = getUtility(IBuilderSet)[name]
        builder.failbuilder(error)
        self._cleanJob(builder.currentjob)

    def dispatch(self, recording_slaves):
        print 'DISPATCHING:', recording_slaves

        self.rounds = 0
        def check_rounds(r):
            self.rounds -= 1
            if self.rounds == 0:
                reactor.stop()

        for slave in recording_slaves:
            proxy = Proxy(
                str(urlappend(slave.url, 'rpc')))
            for method, args in slave.calls:
                self.rounds += 1
                d = proxy.callRemote(method, *args)
                d.addCallback(self.checkDispatch, slave.name)
                d.addErrback(self.dispatchFail, slave.name)
                d.addBoth(check_rounds)

#!/usr/bin/env python
"""Soyuz buildd slave manager logic."""

import logging

from twisted.application import service
from twisted.internet import reactor
from twisted.internet.threads import deferToThread
from twisted.web.xmlrpc import Proxy

from zope.component import getUtility
from zope.security.management import newInteraction

from canonical.launchpad.interfaces.builder import IBuilderSet
from canonical.launchpad.webapp import urlappend
from canonical.librarian.db import read_transaction, write_transaction


class FakeZTM:

    def commit(self):
        pass

    def abort(self):
        pass


class RecordingSlave:

    def __init__(self, name, url):
        self.name = name
        self.url = url
        self.calls = []

    def __repr__(self):
        return '%s - %s' % (self.name, self.url)

    def ensurepresent(self, *args):
        self.calls.append(('ensurepresent', args))
        return (True, 'Download')

    def build(self, *args):
        self.calls.append(('build', args))
        return ('BuilderStatus.BUILDING', args[0])


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
        print 'START'
        deferred = deferToThread(self.scanAllBuilders)
        deferred.addCallback(self.startDispatch)

    @write_transaction
    def scanAllBuilders(self):
        print 'SCAN'
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

            slave = RecordingSlave(builder.name, builder.url)
            builder.setSlaveForTesting(slave)
            builder.dispatchBuildCandidate(candidate)
            recording_slaves.append(slave)

        return recording_slaves

    @write_transaction
    def resetBuilder(self, name):
        builder = getUtility(IBuilderSet)[name]
        job = builder.currentjob
        if job is not None:
            job.builder = None
            job.buildstart = None

    def checkDispatch(self, response, name):
        status, info = response
        if not status:
            print 'FAIL', name, response
            self.resetBuilder(name)

    @write_transaction
    def dispatchFail(self, error, name):
        print 'ERROR'
        builder = getUtility(IBuilderSet)[name]
        builder.failbuilder(error)
        job = builder.currentjob
        if job is not None:
            job.builder = None
            job.buildstart = None

    def startDispatch(self, recording_slaves):
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

        if self.rounds == 0:
            reactor.stop()


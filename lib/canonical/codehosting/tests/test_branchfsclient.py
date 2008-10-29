# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for branchfsclient."""

__metaclass__ = type

import unittest

from twisted.trial.unittest import TestCase

from canonical.codehosting.branchfsclient import CachingAuthserverClient
from canonical.codehosting.inmemory import InMemoryFrontend, XMLRPCWrapper
from canonical.launchpad.interfaces.codehosting import BRANCH_TRANSPORT


class TestCachingAuthserverClient(TestCase):
    """Tests for `CachingAuthserverClient`."""

    def setUp(self):
        frontend = InMemoryFrontend()
        self.factory = frontend.getLaunchpadObjectFactory()
        self.user = self.factory.makePerson()
        self._xmlrpc_client = XMLRPCWrapper(frontend.getFilesystemEndpoint())
        self.client = CachingAuthserverClient(
            self._xmlrpc_client, self.user.id)

    def test_translatePath(self):
        branch = self.factory.makeBranch()
        deferred = self.client.translatePath('/' + branch.unique_name)
        deferred.addCallback(
            self.assertEqual,
            (BRANCH_TRANSPORT, dict(id=branch.id, writable=False), ''))
        return deferred


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


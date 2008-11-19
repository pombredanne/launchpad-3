# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for branchfsclient."""

__metaclass__ = type

import unittest

from twisted.python.failure import Failure
from twisted.trial.unittest import TestCase
from twisted.web.xmlrpc import Fault

from canonical.codehosting.branchfsclient import (
    CachingAuthserverClient, trap_fault)
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


class TestTrapFault(TestCase):
    """Tests for `trap_fault`."""

    def makeFailure(self, exception_factory, *args, **kwargs):
        """Make a `Failure` from the given exception factory."""
        try:
            raise exception_factory(*args, **kwargs)
        except:
            return Failure()

    def assertRaisesFailure(self, failure, function, *args, **kwargs):
        try:
            function(*args, **kwargs)
        except Failure, raised_failure:
            self.assertEqual(failure, raised_failure)

    def test_raises_non_faults(self):
        # trap_fault re-raises any failures it gets that aren't faults.
        failure = self.makeFailure(RuntimeError, 'example failure')
        self.assertRaisesFailure(failure, trap_fault, failure, 235)

    def test_raises_faults_with_wrong_code(self):
        # trap_fault re-raises any failures it gets that are faults but have
        # the wrong fault code.
        failure = self.makeFailure(Fault, 123, 'example failure')
        self.assertRaisesFailure(failure, trap_fault, failure, 235)

    def test_raises_faults_if_no_codes_given(self):
        # If trap_fault is not given any fault codes, it re-raises the fault
        # failure.
        failure = self.makeFailure(Fault, 123, 'example failure')
        self.assertRaisesFailure(failure, trap_fault, failure)

    def test_returns_fault_if_code_matches(self):
        # trap_fault returns the Fault inside the Failure if the fault code
        # matches what's given.
        failure = self.makeFailure(Fault, 123, 'example failure')
        fault = trap_fault(failure, 123)
        self.assertEqual(123, fault.faultCode)
        self.assertEqual('example failure', fault.faultString)

    def test_returns_fault_if_code_matches_one_of_set(self):
        # trap_fault returns the Fault inside the Failure if the fault code
        # matches even one of the given fault codes.
        failure = self.makeFailure(Fault, 123, 'example failure')
        fault = trap_fault(failure, 235, 432, 123, 999)
        self.assertEqual(123, fault.faultCode)
        self.assertEqual('example failure', fault.faultString)



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


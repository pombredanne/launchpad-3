# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0702

"""Tests for branchfsclient."""

__metaclass__ = type

import unittest

from twisted.python.failure import Failure
from twisted.trial.unittest import TestCase

from canonical.codehosting.vfs.branchfsclient import (
    BranchFileSystemClient, NotInCache, trap_fault)
from canonical.codehosting.inmemory import InMemoryFrontend, XMLRPCWrapper
from lp.code.interfaces.codehosting import BRANCH_TRANSPORT
from canonical.launchpad.testing import FakeTime
from canonical.launchpad.xmlrpc.tests.test_faults import (
    TestFaultOne, TestFaultTwo)


class TestBranchFileSystemClient(TestCase):
    """Tests for `BranchFileSystemClient`."""

    def setUp(self):
        frontend = InMemoryFrontend()
        self.factory = frontend.getLaunchpadObjectFactory()
        self.user = self.factory.makePerson()
        self._xmlrpc_client = XMLRPCWrapper(frontend.getFilesystemEndpoint())
        self.fake_time = FakeTime(12345)

    def advanceTime(self, amount):
        """Advance the time seen by clients made by `makeClient` by 'amount'.
        """
        self.fake_time.advance(amount)

    def makeClient(self, expiry_time=None):
        """Make a `BranchFileSystemClient`.

        The created client interacts with the InMemoryFrontend.
        """
        return BranchFileSystemClient(
            self._xmlrpc_client, self.user.id, expiry_time=expiry_time,
            _now=self.fake_time.now)

    def test_translatePath(self):
        branch = self.factory.makeAnyBranch()
        client = self.makeClient()
        deferred = client.translatePath('/' + branch.unique_name)
        deferred.addCallback(
            self.assertEqual,
            (BRANCH_TRANSPORT, dict(id=branch.id, writable=False), ''))
        return deferred

    def test_get_matched_part(self):
        # We cache results based on the part of the URL that the server
        # matched. _getMatchedPart returns that part, based on the path given
        # and the returned data.
        branch = self.factory.makeAnyBranch()
        client = self.makeClient()
        requested_path = '/%s/a/b' % branch.unique_name
        matched_part = client._getMatchedPart(
            requested_path,
            (BRANCH_TRANSPORT, {'id': branch.id, 'writable': False}, 'a/b'))
        self.assertEqual('/%s' % branch.unique_name, matched_part)

    def test_get_matched_part_no_trailing_slash(self):
        # _getMatchedPart always returns the absolute path to the object that
        # the server matched, even if there is no trailing slash and no
        # trailing path.
        #
        # This test is added to exercise a corner case.
        branch = self.factory.makeAnyBranch()
        client = self.makeClient()
        requested_path = '/%s' % branch.unique_name
        matched_part = client._getMatchedPart(
            requested_path,
            (BRANCH_TRANSPORT, {'id': branch.id, 'writable': False}, ''))
        self.assertEqual('/%s' % branch.unique_name, matched_part)

    def test_get_matched_part_no_trailing_path(self):
        # _getMatchedPart always returns the absolute path to the object that
        # the server matched, even if there is a trailing slash and no
        # trailing path.
        #
        # This test is added to exercise a corner case.
        branch = self.factory.makeAnyBranch()
        client = self.makeClient()
        requested_path = '/%s/' % branch.unique_name
        matched_part = client._getMatchedPart(
            requested_path,
            (BRANCH_TRANSPORT, {'id': branch.id, 'writable': False}, ''))
        self.assertEqual('/%s' % branch.unique_name, matched_part)

    def test_path_translation_cache(self):
        # We can retrieve data that we've added to the cache. The data we
        # retrieve looks an awful lot like the data that the endpoint sends.
        branch = self.factory.makeAnyBranch()
        client = self.makeClient()
        fake_data = self.factory.getUniqueString()
        client._addToCache(
            (BRANCH_TRANSPORT, fake_data, ''), '/%s' % branch.unique_name)
        result = client._getFromCache('/%s/foo/bar' % branch.unique_name)
        self.assertEqual(
            (BRANCH_TRANSPORT, fake_data, 'foo/bar'), result)

    def test_path_translation_cache_within_expiry_time(self):
        # If the client treats cached values as having a limited lifetime,
        # repeated requests within that lifetime are served from the cache.
        branch = self.factory.makeAnyBranch()
        expiry_time = 2.0
        client = self.makeClient(expiry_time=expiry_time)
        fake_data = self.factory.getUniqueString()
        client._addToCache(
            (BRANCH_TRANSPORT, fake_data, ''), '/%s' % branch.unique_name)
        self.advanceTime(expiry_time/2)
        result = client._getFromCache('/%s/foo/bar' % branch.unique_name)
        self.assertEqual(
            (BRANCH_TRANSPORT, fake_data, 'foo/bar'), result)

    def test_path_translation_cache_after_expiry_time(self):
        # If the client treats cached values as having a limited lifetime, a
        # request longer than that lifetime after the first is not served from
        # the cache.
        branch = self.factory.makeAnyBranch()
        expiry_time = 2.0
        client = self.makeClient(expiry_time=expiry_time)
        fake_data = self.factory.getUniqueString()
        client._addToCache(
            (BRANCH_TRANSPORT, fake_data, ''), '/%s' % branch.unique_name)
        self.advanceTime(expiry_time*2)
        self.assertRaises(NotInCache, client._getFromCache,
                          '/%s/foo/bar' % branch.unique_name)

    def test_path_translation_cache_respects_path_segments(self):
        # We only get a value from the cache if the cached path is a parent of
        # the requested path. Simple string prefixing is not enough. Added to
        # trap bug 308077.
        branch = self.factory.makeAnyBranch()
        client = self.makeClient()
        fake_data = self.factory.getUniqueString()
        client._addToCache(
            (BRANCH_TRANSPORT, fake_data, ''), '/%s' % branch.unique_name)
        self.assertRaises(
            NotInCache,
            client._getFromCache, '/%s-suffix' % branch.unique_name)

    def test_not_in_cache(self):
        # _getFromCache raises an error when the given path isn't in the
        # cache.
        client = self.makeClient()
        self.assertRaises(
            NotInCache, client._getFromCache, "foo")

    def test_translatePath_retrieves_from_cache(self):
        # If the path already has a prefix in the cache, we use that prefix to
        # translate the path.
        branch = self.factory.makeAnyBranch()
        client = self.makeClient()
        # We'll store fake data in the cache to show that we get data from
        # the cache if it's present.
        fake_data = self.factory.getUniqueString()
        client._addToCache(
            (BRANCH_TRANSPORT, fake_data, ''), '/%s' % branch.unique_name)
        requested_path = '/%s/foo/bar' % branch.unique_name
        deferred = client.translatePath(requested_path)
        def path_translated((transport_type, data, trailing_path)):
            self.assertEqual(BRANCH_TRANSPORT, transport_type)
            self.assertEqual(fake_data, data)
            self.assertEqual('foo/bar', trailing_path)
        return deferred.addCallback(path_translated)

    def test_translatePath_adds_to_cache(self):
        # translatePath adds successful path translations to the cache, thus
        # allowing for future translations to be retrieved from the cache.
        branch = self.factory.makeAnyBranch()
        client = self.makeClient()
        deferred = client.translatePath('/' + branch.unique_name)
        deferred.addCallback(
            self.assertEqual,
            client._getFromCache('/' + branch.unique_name))
        return deferred

    def test_translatePath_control_branch_cache_interaction(self):
        # We don't want the caching to make us mis-interpret paths in the
        # branch as paths into the control transport.
        branch = self.factory.makeAnyBranch()
        client = self.makeClient()
        self.factory.enableDefaultStackingForProduct(branch.product)
        deferred = client.translatePath(
            '/~' + branch.owner.name + '/' + branch.product.name +
            '/.bzr/format')
        def call_translatePath_again(ignored):
            return client.translatePath('/' + branch.unique_name)
        def check_results((transport_type, data, trailing_path)):
            self.assertEqual(BRANCH_TRANSPORT, transport_type)
        deferred.addCallback(call_translatePath_again)
        deferred.addCallback(check_results)
        return deferred

    def test_errors_not_cached(self):
        # Don't cache failed translations. What would be the point?
        client = self.makeClient()
        deferred = client.translatePath('/foo/bar/baz')
        def translated_successfully(result):
            self.fail(
                "Translated successfully. Expected error, got %r" % result)
        def failed_translation(failure):
            self.assertRaises(
                NotInCache, client._getFromCache, '/foo/bar/baz')
        return deferred.addCallbacks(
            translated_successfully, failed_translation)


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
        self.assertRaisesFailure(failure, trap_fault, failure, TestFaultOne)

    def test_raises_faults_with_wrong_code(self):
        # trap_fault re-raises any failures it gets that are faults but have
        # the wrong fault code.
        failure = self.makeFailure(TestFaultOne)
        self.assertRaisesFailure(failure, trap_fault, failure, TestFaultTwo)

    def test_raises_faults_if_no_codes_given(self):
        # If trap_fault is not given any fault codes, it re-raises the fault
        # failure.
        failure = self.makeFailure(TestFaultOne)
        self.assertRaisesFailure(failure, trap_fault, failure)

    def test_returns_fault_if_code_matches(self):
        # trap_fault returns the Fault inside the Failure if the fault code
        # matches what's given.
        failure = self.makeFailure(TestFaultOne)
        fault = trap_fault(failure, TestFaultOne)
        self.assertEqual(TestFaultOne.error_code, fault.faultCode)
        self.assertEqual(TestFaultOne.msg_template, fault.faultString)

    def test_returns_fault_if_code_matches_one_of_set(self):
        # trap_fault returns the Fault inside the Failure if the fault code
        # matches even one of the given fault codes.
        failure = self.makeFailure(TestFaultOne)
        fault = trap_fault(failure, TestFaultOne, TestFaultTwo)
        self.assertEqual(TestFaultOne.error_code, fault.faultCode)
        self.assertEqual(TestFaultOne.msg_template, fault.faultString)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


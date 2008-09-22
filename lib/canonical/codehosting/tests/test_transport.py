# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0231

"""Tests for the Launchpad code hosting Bazaar transport."""

__metaclass__ = type

import unittest

from bzrlib.tests import test_transport_implementations
from bzrlib.transport import chroot, get_transport, Transport
from bzrlib.transport.memory import MemoryTransport

from canonical.codehosting.branchfs import LaunchpadInternalServer
from canonical.codehosting.branchfsclient import BlockingProxy
from canonical.codehosting.tests.helpers import (
    FakeLaunchpad, TestResultWrapper)


class TestingServer(LaunchpadInternalServer):
    """A Server that provides instances of LaunchpadTransport for testing.

    See the comment in `_transportFactory` about what we actually test and
    `TestLaunchpadTransportImplementation` for the actual TestCase class.
    """

    def __init__(self):
        """Initialize the server.

        We register ourselves with the scheme lp-testing=${id(self)}:///
        using the `FakeLaunchpad` authserver client and backed onto a
        MemoryTransport.
        """
        LaunchpadInternalServer.__init__(
            self, 'lp-testing-%s:///' % id(self),
            BlockingProxy(FakeLaunchpad()), MemoryTransport())
        self._chroot_servers = []

    def _transportFactory(self, url):
        """See `LaunchpadInternalServer._transportFactory`.

        As `LaunchpadTransport` 'acts all kinds of crazy' above the .bzr
        directory of a branch (forbidding file or directory creation at some
        levels, enforcing naming restrictions at others), we test a
        LaunchpadTransport chrooted into the .bzr directory of a branch.
        """
        if url != self._scheme:
            raise AssertionError(
                "Don't know how to create non-root transport. Not needed for "
                "testing.")
        root_transport = LaunchpadInternalServer._transportFactory(self, url)
        # We clone to this particular URL because FakeLaunchpad's constructor
        # creates a branch with this URL.  This is an instance of the Mystery
        # Guest test anti-pattern.
        bzrdir_transport = root_transport.clone('~testuser/firefox/qux/.bzr')
        bzrdir_transport.ensure_base()
        chroot_server = chroot.ChrootServer(bzrdir_transport)
        chroot_server.setUp()
        self._chroot_servers.append(chroot_server)
        return get_transport(chroot_server.get_url())

    def tearDown(self):
        """See `LaunchpadInternalServer.tearDown`.

        In addition to calling the overridden method, we tear down any
        ChrootServer instances we've set up.
        """
        for chroot_server in self._chroot_servers:
            chroot_server.tearDown()
        LaunchpadInternalServer.tearDown(self)


class TestLaunchpadTransportImplementation(
        test_transport_implementations.TransportTests):
    """Implementation tests for `LaunchpadTransport`.

    We test the transport chrooted to the .bzr directory of a branch -- see
    `TestingServer._transportFactory` for more.
    """
    # TransportTests tests that get_transport() returns an instance of
    # `transport_class`, but the instances we're actually testing are
    # instances of ChrootTransport wrapping instances of SynchronousAdapter
    # which wraps the LaunchpadTransport we're actually interested in.  This
    # doesn't seem interesting to check, so we just set transport_class to
    # the base Transport class.
    transport_class = Transport

    def setUp(self):
        """Arrange for `get_transport` to return wrapped LaunchpadTransports.
        """
        self.transport_server = TestingServer
        super(TestLaunchpadTransportImplementation, self).setUp()

    def run(self, result=None):
        """Run the test, with the result wrapped so that it knows about skips.
        """
        if result is None:
            result = self.defaultTestResult()
        super(TestLaunchpadTransportImplementation, self).run(
            TestResultWrapper(result))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

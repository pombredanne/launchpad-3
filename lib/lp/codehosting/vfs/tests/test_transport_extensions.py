# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for extensions in codehosting.vfs.transport."""

__metaclass__ = type

import unittest

from bzrlib.transport.memory import MemoryTransport

from lp.codehosting.vfs.transport import get_readonly_transport
from canonical.launchpad.testing import TestCase


class TestReadOnly(TestCase):
    """Tests for get_readonly_transport."""

    def test_makes_readonly_transport(self):
        # get_readonly_transport wraps a transport so that its readonly.
        transport = MemoryTransport()
        self.assertEqual(False, transport.is_readonly())
        readonly_transport = get_readonly_transport(transport)
        self.assertEqual(True, readonly_transport.is_readonly())

    def test_only_wraps_once(self):
        # get_readonly_transport just returns the given transport if its
        # already readonly.
        transport = MemoryTransport()
        readonly_transport = get_readonly_transport(transport)
        double_readonly = get_readonly_transport(readonly_transport)
        self.assertIs(readonly_transport, double_readonly)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


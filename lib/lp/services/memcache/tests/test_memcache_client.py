# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the IMemcacheClient utility."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.services.memcache.interfaces import IMemcacheClient
from lp.testing import TestCase


class MemcacheClientTestCase(TestCase):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(MemcacheClientTestCase, self).setUp()
        self.client = getUtility(IMemcacheClient)

    def test_basics(self):
        self.assertTrue(self.client.set('somekey', 'somevalue'))
        self.assertEqual(self.client.get('somekey'), 'somevalue')

    def test_bug_452092(self):
        """Memcache 1.44 allowed spaces in keys, which was incorrect. This
        would break things badly enough that we are running a patched version.
        This test ensures that spaces are correctly flagged as errors at
        the callsite rather than causing chaos later, ensuring that if
        we upgrade we upgrade to a version with correct validation.
        """
        self.assertRaises(
            self.client.MemcachedKeyCharacterError,
            self.client.set, 'key with spaces', 'some value')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


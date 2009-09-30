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
        self.client = getUtility(IMemcacheClient)

    def test_basics(self):
        self.assertTrue(self.client.set('somekey', 'somevalue'))
        self.assertEqual(self.client.get('somekey'), 'somevalue')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


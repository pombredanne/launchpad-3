# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.testing import TestCaseWithFactory


class MemcacheTestCase(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def assertCacheMiss(self, fragment, content):
        # Verify that fragment is not cached in the content.
        self.assertTrue(fragment in content)
        before, after = content.split(fragment, 1)
        cache_start = '<!-- Cache hit: memcache expression'
        if cache_start in before:
            # Verify that the preceding cache is not for this fragment
            cache_end = '<!-- End cache hit'
            self.assertTrue(cache_end in before)
            ignore, start = before.rsplit(cache_end, 1)
            self.assertTrue(cache_start not in start)

    def assertCacheHit(self, fragment, expression, content):
        # Verify that fragment is cached by the specific expression in
        # the content.
        self.assertTrue(fragment in content)
        before, after = content.split(fragment, 1)
        cache_start = (
            '<!-- Cache hit: memcache expression (%s) ' % expression)
        self.assertTrue(cache_start in before)
        ignore, start = before.rsplit(cache_start, 1)
        self.assertTrue('<!-- End cache hit' not in start)

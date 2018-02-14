# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'MemcacheFixture',
    ]

import fixtures

from lp.services.memcache.interfaces import IMemcacheClient
from lp.testing.fixture import ZopeUtilityFixture


class MemcacheFixture(fixtures.Fixture):
    """A trivial in-process memcache fixture."""

    def __init__(self):
        self._cache = {}

    def _setUp(self):
        self.useFixture(ZopeUtilityFixture(self, IMemcacheClient))

    def get(self, key):
        return self._cache.get(key)

    def set(self, key, val):
        self._cache[key] = val
        return 1

    def delete(self, key):
        self._cache.pop(key, None)
        return 1

    def clear(self):
        self._cache = {}

# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Storm/memcached implementation of lazr.restful's representation cache."""

import storm

from lp.services.memcache.client import memcache_client_factory
from lazr.restful.simple import BaseRepresentationCache

__metaclass__ = type
__all__ = [
    'MemcachedStormRepresentationCache',
]


class MemcachedStormRepresentationCache(BaseRepresentationCache):
    """Caches lazr.restful representations of Storm objects in memcached."""

    def __init__(self):
        self.client = memcache_client_factory()

    def key_for(self, obj, media_type, version):
        storm_info = storm.info.get_obj_info(obj)
        table_name = storm_info.cls_info.table
        primary_key = tuple(var.get() for var in storm_info.primary_vars)

        key = (table_name + repr(primary_key)
                + ',' + media_type + ',' + str(version))
        return key

    def get_by_key(self, key, default=None):
        return self.client.get(key) or default

    def set_by_key(self, key, value):
        self.client.set(key, value)

    def delete_by_key(self, key):
        self.client.delete(key)

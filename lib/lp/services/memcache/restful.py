# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Storm/memcached implementation of lazr.restful's representation cache."""

import storm

from zope.component import getUtility

from canonical.config import config
from lp.services.memcache.interfaces import IMemcacheClient
from lazr.restful.simple import BaseRepresentationCache

__metaclass__ = type
__all__ = [
    'MemcachedStormRepresentationCache',
]


class MemcachedStormRepresentationCache(BaseRepresentationCache):
    """Caches lazr.restful representations of Storm objects in memcached."""

    def __init__(self):
        """Initialize with the memcached client."""
        self.client = getUtility(IMemcacheClient)

    def key_for(self, obj, media_type, version):
        """See `BaseRepresentationCache`."""
        storm_info = storm.info.get_obj_info(obj)
        table_name = storm_info.cls_info.table
        primary_key = tuple(var.get() for var in storm_info.primary_vars)

        key = (table_name + repr(primary_key)
               + ',' + config._instance_name
               + ',' + media_type + ',' + str(version))
        return key

    def get_by_key(self, key, default=None):
        """See `BaseRepresentationCache`."""
        return self.client.get(key) or default

    def set_by_key(self, key, value):
        """See `BaseRepresentationCache`."""
        self.client.set(
            key, value,
            time=config.vhost.api.representation_cache_expiration_time)

    def delete_by_key(self, key):
        """See `BaseRepresentationCache`."""
        self.client.delete(key)

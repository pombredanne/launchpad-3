# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Launchpad Memcache client."""

__metaclass__ = type
__all__ = []

import memcache
import re

from canonical.config import config


def memcache_client_factory():
    """Return a memcache.Client for Launchpad."""
    servers = [
        (host, int(weight)) for host, weight in re.findall(
            r'\((.+?),(\d+)\)', config.memcache.servers)]
    assert len(servers) > 0, "Invalid memcached server list %r" % (
        config.memcache.addresses,)
    return memcache.Client(servers)

# Copyright 2009 Canonical Ltd.  All rights reserved.

"""OpenID Consumer related database classes."""

__metaclass__ = type
__all__ = ['OpenIDNonce']

from storm.locals import DateTime, Int, Storm, Unicode

class OpenIDNonce(Storm):
    """An OpenIDNonce.

    The table definition matches that required by the openid library,
    so doesn't follow our standards. In particular, it doesn't have an
    id column and the timestamp is an epoch time integer rather than a
    datetime.
    """
    __storm_table__ = "OpenIDNonce"
    __storm_primary__ = "server_url", "timestamp", "salt"

    server_url = Unicode()
    timestamp = Int()
    salt = Unicode()

# Copyright 2009 Canonical Ltd.  All rights reserved.

"""OpenID Consumer related database classes."""

__metaclass__ = type
__all__ = ['OpenIDNonce']

from storm.locals import DateTime, Int, Storm, Unicode

class OpenIDNonce(Storm):
    """An OpenIDNonce.

    The table definition matches that required by the openid library,
    so doesn't follow our standards.
    """
    __storm_table__ = "OpenIDNonce"

    id = Int(primary=True)

    server_url = Unicode()
    timestamp = Int()
    salt = Unicode()

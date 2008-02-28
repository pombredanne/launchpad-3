# Copyright 2004 Canonical Ltd.  All rights reserved.

"""Client APIs for the authserver.

While the authserver is just XML-RPC, there is still some boilerplate that can
be reduced by putting common code in this package.
"""

# TODO:
#   - refactor authserver client code in shipit to live here
#   - Twisted XML-RPC client stuff for supermirror SFTP server.

__all__ = [
    'get_blocking_proxy',
    'get_twisted_proxy',
    'InMemoryBlockingProxy',
    'InMemoryTwistedProxy']

from canonical.authserver.client.proxy import *


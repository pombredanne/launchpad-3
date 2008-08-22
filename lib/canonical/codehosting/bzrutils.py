# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Utilities for dealing with Bazaar.

Everything in here should be submitted upstream.
"""

__metaclass__ = type
__all__ = [
    'ensure_base',
    'HttpAsLocalTransport',
    ]

from bzrlib.builtins import _create_prefix as create_prefix
from bzrlib.errors import NoSuchFile
from bzrlib.transport import register_transport, unregister_transport
from bzrlib.transport.local import LocalTransport

from canonical.launchpad.webapp.uri import URI


# XXX: JonathanLange 2007-06-13 bugs=120135:
# This should probably be part of bzrlib.
def ensure_base(transport):
    """Make sure that the base directory of `transport` exists.

    If the base directory does not exist, try to make it. If the parent of the
    base directory doesn't exist, try to make that, and so on.
    """
    try:
        transport.ensure_base()
    except NoSuchFile:
        create_prefix(transport)


class HttpAsLocalTransport(LocalTransport):
    """A LocalTransport that works using http URLs.

    We have this because the Launchpad database has constraints on URLs for
    branches, disallowing file:/// URLs. bzrlib itself disallows
    file://localhost/ URLs.
    """

    def __init__(self, http_url):
        file_url = URI(
            scheme='file', host='', path=URI(http_url).path)
        return super(HttpAsLocalTransport, self).__init__(
            str(file_url))

    @classmethod
    def register(cls):
        """Register this transport."""
        register_transport('http://', cls)

    @classmethod
    def unregister(cls):
        """Unregister this transport."""
        unregister_transport('http://', cls)

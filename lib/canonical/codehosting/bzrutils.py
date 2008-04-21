# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Utilities for dealing with Bazaar.

Everything in here should be submitted upstream.
"""

__metaclass__ = type
__all__ = [
    'ensure_base',
    'makedirs'
    ]

from bzrlib.builtins import _create_prefix as create_prefix
from bzrlib.errors import FileExists, NoSuchFile


def ensure_base(transport):
    """Make sure that the base directory of `transport` exists.

    If the base directory does not exist, try to make it. If the parent of the
    base directory doesn't exist, try to make that, and so on.
    """
    try:
        transport.ensure_base()
    except NoSuchFile:
        create_prefix(transport)


# XXX: JonathanLange 2007-06-13 bugs=120135:
# This should probably be part of bzrlib.
def makedirs(base_transport, path, mode=None):
    """Create 'path' on 'base_transport', even if parents of 'path' don't
    exist yet.
    """
    need_to_create = []
    transport = base_transport.clone(path)
    while True:
        try:
            transport.mkdir('.', mode)
        except NoSuchFile:
            need_to_create.append(transport)
        except FileExists:
            # Nothing to do. Directory made.
            return
        else:
            break
        transport = transport.clone('..')
    while need_to_create:
        transport = need_to_create.pop()
        transport.mkdir('.', mode)

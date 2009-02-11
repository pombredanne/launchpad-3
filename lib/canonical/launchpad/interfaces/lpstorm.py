# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Storm marker interfaces."""

__metaclass__ = type
__all__ = [
    'IDBObject', 'IMasterDBObject', 'IMasterStore', 'ISlaveStore', 'IStore',
    ]


from storm.locals import Storm
from storm.store import Store

from zope.interface import classImplements, directlyProvides, Interface
from zope.interface.interfaces import IInterface


class IStore(Interface):
    """A storm.store.Store."""
    def get(cls, key):
        """See storm.store.Store."""


class IMasterStore(IStore):
    """A writeable Storm Stores."""


class ISlaveStore(IStore):
    """A read-only Storm Store."""


class IDBObject(Interface):
    """A Storm database object."""


class IMasterDBObject(IDBObject):
    """A Storm database object associated with its master Store."""


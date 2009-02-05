# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Storm marker interfaces."""

__metaclass__ = type
__all__ = [
    'IMasterStore', 'ISlaveStore', 'IStore',
    ]


from storm.locals import Storm
from storm.store import Store

from zope.interface import classImplements, directlyProvides, Interface
from zope.interface.interfaces import IInterface


class IStore(Interface):
    """Marker interface implemented by storm.store.Store."""
classImplements(Store, IStore)


class IMasterStore(IStore):
    """Marker interface for writeable Stores."""


class ISlaveStore(IStore):
    """Marker interface for read-only Stores."""


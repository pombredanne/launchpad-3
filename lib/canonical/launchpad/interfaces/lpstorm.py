# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Storm marker interfaces."""

__metaclass__ = type
__all__ = [
    'IDBObject', 'IMasterObject', 'IMasterStore', 'ISlaveStore', 'IStore',
    ]


from zope.interface import Interface


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


class IMasterObject(IDBObject):
    """A Storm database object associated with its master Store."""

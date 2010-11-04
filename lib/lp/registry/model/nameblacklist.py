# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Classes for managing the NameBlackList table."""

__metaclass__ = type
__all__ = [
    'NameBlackList',
    'NameBlackListSet',
    ]


from storm.base import Storm
from storm.locals import (
    Int,
    Unicode,
    )

from zope.interface import implements

from canonical.launchpad.interfaces.lpstorm import IStore

from lp.registry.interfaces.nameblacklist import (
    INameBlackList,
    INameBlackListSet,
    )


class NameBlackList(Storm):
    """Class for the NameBlackList table."""

    implements(INameBlackList)

    __storm_table__ = 'NameBlackList'

    id = Int(primary=True)
    regexp = Unicode(name='regexp', allow_none=False)
    comment = Unicode(name='comment', allow_none=True)


class NameBlackListSet:
    """Class for creating and retrieving NameBlackList objects."""

    implements(INameBlackListSet)

    def create(self, regexp, comment=None):
        """See `INameBlackListSet`."""
        nameblacklist = NameBlackList()
        nameblacklist.regexp = regexp
        nameblacklist.comment = comment
        store = IStore(NameBlackList)
        store.add(nameblacklist)
        return nameblacklist

    def get(self, id):
        """See `INameBlackListSet`."""
        store = IStore(NameBlackList)
        return store.find(NameBlackList, NameBlackList.id == id).one()

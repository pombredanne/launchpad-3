# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['ManifestAncestry']

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import IManifestAncestry


class ManifestAncestry(SQLBase):
    """A ManifestAncestry relates a Manifest with another."""

    implements(IManifestAncestry)

    _table = 'ManifestAncestry'

    parent = ForeignKey(foreignKey='Manifest',
                        dbName='parent',
                        notNull=True)
    child = ForeignKey(foreignKey='Manifest',
                       dbName='child',
                       notNull=True)

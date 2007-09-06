# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['ManifestEntry']

from zope.interface import implements

from sqlobject import StringCol, ForeignKey, IntCol

from canonical.database.sqlbase import SQLBase
from canonical.database.enumcol import EnumCol

from canonical.lp.dbschema import ManifestEntryType, ManifestEntryHint

from canonical.launchpad.interfaces import IManifestEntry


class ManifestEntry(SQLBase):
    """A single entry in a manifest"""

    implements(IManifestEntry)

    _table = 'ManifestEntry'

    manifest = ForeignKey(foreignKey='Manifest', dbName='manifest',
                   notNull=True)
    sequence = IntCol(dbName='sequence', notNull=True)
    branch = ForeignKey(foreignKey='Branch', dbName='branch')
    changeset = ForeignKey(foreignKey='Changeset', dbName='changeset')

    entrytype = EnumCol(dbName='entrytype', notNull=True,
                        schema=ManifestEntryType)
    hint = EnumCol(dbName='hint', notNull=False,
                   schema=ManifestEntryHint)
    path = StringCol(dbName='path', notNull=True)
    parent = IntCol(dbName='parent')
    dirname = StringCol(dbName='dirname')


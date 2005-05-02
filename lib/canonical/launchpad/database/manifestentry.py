# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['ManifestEntry']

from zope.interface import implements

from sqlobject import StringCol, ForeignKey, IntCol

from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import IManifestEntry

# See below.  Can use EnumCol when it doesn't break banzai.
#
#from canonical.lp.dbschema import EnumCol
#from canonical.lp.dbschema import ManifestEntryType


class ManifestEntry(SQLBase):
    """A single entry in a manifest"""

    implements(IManifestEntry)

    _table = 'ManifestEntry'

    manifest = ForeignKey(foreignKey='Manifest', dbName='manifest', 
                   notNull=True)
    sequence = IntCol(dbName='sequence', notNull=True)
    branch = ForeignKey(foreignKey='Branch', dbName='branch')
    changeset = ForeignKey(foreignKey='Changeset', dbName='changeset')

    # XXX: Daniel Debonzi 2005-03-23
    # Could not change to EnumCol because it breaks banzai
    # which I am not supose to hack.
    # Fix it ASA banzai is changed.
    # file: banzai/backends/launchpad.py
    # method: newManifestEntry
    ##entrytype = EnumCol(dbName='entrytype', notNull=True,
    ##                    schema=ManifestEntryType)
    entrytype = IntCol(dbName='entrytype', notNull=True)
    path = StringCol(dbName='path', notNull=True)
    patchon = IntCol(dbName='patchon')
    dirname = StringCol(dbName='dirname')


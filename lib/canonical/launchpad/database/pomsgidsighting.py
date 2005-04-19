# Zope interfaces
from zope.interface import implements

# SQL imports
from sqlobject import ForeignKey, IntCol, BoolCol
from canonical.database.sqlbase import SQLBase
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.interfaces import IPOMsgIDSighting

class POMsgIDSighting(SQLBase):
    implements(IPOMsgIDSighting)

    _table = 'POMsgIDSighting'

    potmsgset = ForeignKey(foreignKey='POTMsgSet', dbName='potmsgset',
        notNull=True)
    pomsgid_ = ForeignKey(foreignKey='POMsgID', dbName='pomsgid',
        notNull=True)
    datefirstseen = UtcDateTimeCol(dbName='datefirstseen', notNull=True)
    datelastseen = UtcDateTimeCol(dbName='datelastseen', notNull=True)
    inlastrevision = BoolCol(dbName='inlastrevision', notNull=True)
    pluralform = IntCol(dbName='pluralform', notNull=True)


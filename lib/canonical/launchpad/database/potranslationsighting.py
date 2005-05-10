# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['POTranslationSighting']

from zope.interface import implements

from sqlobject import DateTimeCol, ForeignKey, IntCol, BoolCol
from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import IPOTranslationSighting
from canonical.lp.dbschema import EnumCol
from canonical.database.constants import DEFAULT
from canonical.lp.dbschema import RosettaTranslationOrigin


class POTranslationSighting(SQLBase):
    implements(IPOTranslationSighting)

    _table = 'POTranslationSighting'

    pomsgset = ForeignKey(foreignKey='POMsgSet', dbName='pomsgset',
        notNull=True)
    potranslation = ForeignKey(foreignKey='POTranslation',
        dbName='potranslation', notNull=True)
    license = IntCol(dbName='license', notNull=False, default=None)
    datefirstseen = DateTimeCol(dbName='datefirstseen', notNull=True)
    datelastactive = DateTimeCol(dbName='datelastactive', notNull=True)
    inlastrevision = BoolCol(dbName='inlastrevision', notNull=True)
    pluralform = IntCol(dbName='pluralform', notNull=True)
    active = BoolCol(dbName='active', notNull=True, default=DEFAULT)
    # See canonical.lp.dbschema.RosettaTranslationOrigin.
    origin = EnumCol(dbName='origin', notNull=True,
        schema=RosettaTranslationOrigin)
    person = ForeignKey(foreignKey='Person', dbName='person', notNull=True)


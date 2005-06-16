# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['POSubmission']

from zope.interface import implements

from sqlobject import DateTimeCol, ForeignKey, IntCol, BoolCol
from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import IPOSubmission
from canonical.lp.dbschema import EnumCol
from canonical.database.constants import DEFAULT, UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.lp.dbschema import RosettaTranslationOrigin


class POSubmission(SQLBase):

    implements(IPOSubmission)
    _table = 'POSubmission'

    pomsgset = ForeignKey(foreignKey='POMsgSet',
        dbName='pomsgset', notNull=True)
    pluralform = IntCol(notNull=True)
    potranslation = ForeignKey(foreignKey='POTranslation',
        dbName='potranslation', notNull=True)
    datecreated = UtcDateTimeCol(
        dbName='datecreated', notNull=True, default=UTC_NOW)
    origin = EnumCol(dbName='origin', notNull=True,
        schema=RosettaTranslationOrigin)
    person = ForeignKey(foreignKey='Person', dbName='person', notNull=True)

# XXX do we want to indicate the difference between a from-scratch
# submission and an editorial decision (for example, when someone is
# reviewing a file and says "yes, let's use that one")?


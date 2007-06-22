# Copyright 2005-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'POSubmission',
    'POSubmissionSet'
    ]

from zope.interface import implements

from sqlobject import (
    BoolCol, ForeignKey, IntCol, SQLMultipleJoin, SQLObjectNotFound)

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol

from canonical.lp.dbschema import (RosettaTranslationOrigin,
    TranslationValidationStatus)

from canonical.launchpad.interfaces import IPOSubmission, IPOSubmissionSet


class POSubmissionSet:

    implements(IPOSubmissionSet)

    def getPOSubmissionByID(self, id):
        """See IPOSubmissionSet."""
        try:
            return POSubmission.get(id)
        except SQLObjectNotFound:
            return None


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
    validationstatus = EnumCol(dbName='validationstatus', notNull=True,
        schema=TranslationValidationStatus)
    active = BoolCol(notNull=True, default=False)
    published = BoolCol(notNull=True, default=False)

    def makeHtmlId(self, description, for_potmsgset=None):
        """See `IPOSubmission`."""
        if for_potmsgset is None:
            for_potmsgset = self.pomsgset.potmsgset
        suffix = '_'.join([
            self.pomsgset.pofile.language.code,
            description,
            str(self.id),
            str(self.pluralform)])
        return for_potmsgset.makeHtmlId(suffix)


# XXX do we want to indicate the difference between a from-scratch
# submission and an editorial decision (for example, when someone is
# reviewing a file and says "yes, let's use that one")?


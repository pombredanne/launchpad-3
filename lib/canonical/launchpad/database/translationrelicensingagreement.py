# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'TranslationRelicensingAgreement',
    ]

from zope.interface import implements
from sqlobject import BoolCol, ForeignKey

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces.translationrelicensingagreement import (
    ITranslationRelicensingAgreement)
from canonical.launchpad.validators.person import public_person_validator


class TranslationRelicensingAgreement(SQLBase):
    implements(ITranslationRelicensingAgreement)

    _table = 'TranslationRelicensingAgreement'

    person = ForeignKey(
        foreignKey='Person',
        validator=public_person_validator, dbName='person', notNull=True)

    allow_relicensing = BoolCol(dbName='allow_relicensing',
                                notNull=True, default=True)

    date_decided = UtcDateTimeCol(
        dbName='date_decided', notNull=True, default=UTC_NOW)

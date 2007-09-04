# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Language pack store."""

__metaclass__ = type

__all__ = [
    'LanguagePack',
    ]

from sqlobject import ForeignKey
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import ILanguagePack, LanguagePackType


class LanguagePack(SQLBase):
    implements(ILanguagePack)

    _table = 'LanguagePack'

    language_pack_file = ForeignKey(
        foreignKey='LibraryFileAlias', dbName='language_pack_file',
        notNull=True)

    date_exported = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    distro_series = ForeignKey(
        foreignKey='DistroRelease', dbName='distro_release',
        notNull=True)

    language_pack_type = EnumCol(
        schema=LanguagePackType, notNull=True, default=LanguagePackType.FULL)

    language_pack_that_updates = ForeignKey(
        foreignKey='LanguagePack', dbName='language_pack_that_updates',
        notNull=False, default=None)

# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Language pack store."""

__metaclass__ = type

__all__ = [
    'LanguagePack',
    'LanguagePackSet',
    ]

from sqlobject import ForeignKey
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.interfaces import (
    ILanguagePack, ILanguagePackSet, LanguagePackType)


class LanguagePack(SQLBase):
    implements(ILanguagePack)

    _table = 'LanguagePack'

    file = ForeignKey(
        foreignKey='LibraryFileAlias', dbName='file', notNull=True)

    date_exported = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    distroseries = ForeignKey(
        foreignKey='DistroSeries', dbName='distroseries', notNull=True)

    type = EnumCol(
        enum=LanguagePackType, notNull=True, default=LanguagePackType.FULL)

    updates = ForeignKey(
        foreignKey='LanguagePack', dbName='updates',
        notNull=False, default=None)


class LanguagePackSet:
    implements(ILanguagePackSet)

    def addLanguagePack(self, distroseries, file_alias, type):
        """See `ILanguagePackSet`."""
        assert type in LanguagePackType, (
            'Unknown language pack type: %s' % type.name)

        if (type == LanguagePackType.DELTA and
            distroseries.language_pack_base is None):
            raise AssertionError(
                "There is no base language pack available for %s's %s to get"
                " deltas from." % sqlvalues(
                    distroseries.distribution.name, distroseries.name))

        updates = None
        if type == LanguagePackType.DELTA:
            updates = distroseries.language_pack_base

        return LanguagePack(
            file=file_alias, date_exported=UTC_NOW, distroseries=distroseries,
            type=type, updates=updates)

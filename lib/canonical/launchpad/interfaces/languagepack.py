# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Language pack store."""

__metaclass__ = type

__all__ = [
    'ILanguagePack',
    'ILanguagePackSet',
    'LanguagePackType',
    ]

from zope.schema import Choice, Datetime, Int, Object
from zope.interface import Attribute, Interface

from canonical.launchpad import _
from canonical.launchpad.interfaces.librarian import ILibraryFileAlias
from canonical.lazr import DBEnumeratedType, DBItem


class LanguagePackType(DBEnumeratedType):
    """Type of language packs."""

    FULL = DBItem(1, """
        Full

        Full translations export.""")

    DELTA = DBItem(2, """
        Delta

        Delta translation export based on a previous full export.""")


class ILanguagePackSet(Interface):
    """Language pack store set."""

    def addLanguagePack(distroseries, file_alias, type):
        """Add a new language pack to our records.

        :param distroseries: The `IDistroSeries` associated from where this
            language pack comes.
        :param file_alias: An `ILibraryFileAlias` pointing to the librarian
            entry storing the language pack we want to register.
        :param type: The kind of `LanguagePackType` for this language pack.
        :return: An `ILanguagePack` representing the given language pack.
        """


class ILanguagePack(Interface):
    """Language pack store."""

    id = Int(title=_('Language pack ID.'), required=True, readonly=True)

    file = Object(
        title=_('Librarian file where the language pack is stored.'),
        required=True, schema=ILibraryFileAlias)

    date_exported = Datetime(
        title=_('When this language pack was exported.'),
        required=True)

    distroseries = Choice(
        title=_('The distribution series from where it was exported.'),
        required=True, vocabulary='FilteredDistroSeries')

    type = Choice(
        title=_('Language pack type'), required=True,
        vocabulary=LanguagePackType,
        description=_("""
            Type of language pack. There are two types available, 1: Full
            export, 2: Update export based on `updates` export.
            """))

    updates = Attribute(_('The LanguagePack that this one updates.'))

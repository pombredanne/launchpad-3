# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Language pack store."""

__metaclass__ = type

__all__ = [
    'ILanguagePack',
    'LanguagePackType',
    ]

from zope.schema import Choice, Datetime, Object
from zope.interface import Interface

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


class ILanguagePack(Interface):
    """Language pack store."""

    language_pack_file = Object(
        title=_('Librarian file where the language pack is stored.'),
        required=True, schema=ILibraryFileAlias)

    date_exported = Datetime(
        title=_('When this language pack was exported.'),
        required=True)

    distro_release = Choice(
        title=_('The distribution series from where it was exported.'),
        required=True, vocabulary='FilteredDistroSeries')

    language_pack_type = Choice(
        title=_('Language pack type'), required=True,
        vocabulary=LanguagePackType,
        description=_("""
            Type of language pack. There are two types available, 1: Full
            export, 2: Update export based on language_pack_that_updates
            export.
            """))

    language_pack_that_updates = Object(
        title=_('The LanguagePack that this one updates.'),
        required=True, schema=ILanguagePack)

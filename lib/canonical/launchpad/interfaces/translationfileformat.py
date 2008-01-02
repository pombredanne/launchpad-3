# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Enumeration type for translation file formats."""

__metaclass__ = type
__all__ = ['TranslationFileFormat']


from canonical.lazr import DBEnumeratedType, DBItem


class TranslationFileFormat(DBEnumeratedType):
    """Translation File Format

    This is an enumeration of the different sorts of file that Launchpad
    Translations knows about.
    """

    PO = DBItem(1, """
        PO format

        Gettext's standard text file format.
        """)

    MO = DBItem(2, """
        MO format

        Gettext's standard binary file format.
        """)

    XPI = DBItem(3, """
        Mozilla XPI format

        The .xpi format as used by programs from Mozilla foundation.
        """)

    KDEPO = DBItem(4, """
        KDE PO format

        Legacy KDE PO format which embeds context and plural forms inside
        messages itself instead of using gettext features.
        """)


# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute

__metaclass__ = type

__all__ = ('ICanAttachRawFileData', 'IRawFileData')

class ICanAttachRawFileData(Interface):
    """Accept .po or .pot attachments."""

    def attachRawFileData(contents, importer=None):
        """Attach a .pot/.po file to be imported later with doRawImport call.

        The content is parsed first with the POParser, if it has any problem
        the POSyntaxError or POInvalidInputError exeption will be raised.
        """

class IRawFileData(Interface):
    """Represent a raw file data from a .po or .pot file."""

    rawfile = Attribute("The pot/po file itself in raw mode.")

    rawimporter = Attribute("The person that attached the rawfile.")

    daterawimport = Attribute("The date when the rawfile was attached.")

    rawimportstatus = Attribute(
        "The status of the import: 1 ignore import, 2 pending to be imported,"
        " 3 imported already and 4 failed.")

    def doRawImport(logger=None):
        """Execute the import of the rawfile field, if it's needed.

        If a logger argument is given, log there any problem found with the
        import.
        """

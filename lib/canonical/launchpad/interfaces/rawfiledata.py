# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute

__metaclass__ = type

__all__ = ('RawFileAttachFailed', 'RawFileFetchFailed',
    'ICanAttachRawFileData', 'IRawFileData')

class RawFileAttachFailed(Exception):
    pass

class RawFileFetchFailed(Exception):
    pass

class ICanAttachRawFileData(Interface):
    """Accept .po or .pot attachments."""

    def attachRawFileData(contents, published, importer=None):
        """Attach a PO template or PO file to be imported later.

        The content is parsed first with the PO parser. If it has any problem
        a POSyntaxError or POInvalidInputError exeption will be raised.

        The "published" flag indicates whether or not this attachment is an
        upload by a translator of their own translations, or the published
        PO file. setting published=False on a POTemplate will cause a
        POInvalidInputError.

        If there is any problem storing the attached file, a
        RawFileAttachFailed exception will be raised.
        """

class IRawFileData(Interface):
    """Represent a raw file data from a .po or .pot file."""

    rawfile = Attribute("The pot/po file itself in raw mode.")

    rawimporter = Attribute("The person that attached the rawfile.")

    daterawimport = Attribute("The date when the rawfile was attached.")

    rawfilepublished = Attribute("Whether or not the rawfile was the "
        "published version, or just translations from an editor.")

    rawimportstatus = Attribute(
        "The status of the import. See RosettaImportStatus for allowable"
        " values.")

    def doRawImport(logger=None):
        """Execute the import of the rawfile field, if it's needed.

        If a logger argument is given, any problem found with the
        import will be logged there.

        If there is problem fetching the attached file, a RawFileFetchFailed
        exception will be raised.
        """


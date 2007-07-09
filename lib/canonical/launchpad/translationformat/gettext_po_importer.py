# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'GettextPoImporter'
    ]

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import ITranslationFormatImporter
from canonical.launchpad.translationformat.gettext_po_parser import (
    PoParser, PoHeader)
from canonical.librarian.interfaces import ILibrarianClient
from canonical.lp.dbschema import TranslationFileFormat


class GettextPoImporter:
    """Support class to import gettext .po files."""
    implements(ITranslationFormatImporter)

    def __init__(self, context=None):
        self.basepath = None
        self.productseries = None
        self.distroseries = None
        self.sourcepackagename = None
        self.is_published = False
        self.content = None

    @property
    def format(self):
        """See `ITranslationFormatImporter`."""
        return TranslationFileFormat.PO

    @property
    def content_type(self):
        """See `ITranslationFormatImporter`."""
        return 'application/x-po'

    @property
    def file_extensions(self):
        """See `ITranslationFormatImporter`."""
        return ['.po', '.pot']

    @property
    def has_alternative_msgid(self):
        """See `ITranslationFormatImporter`."""
        return False

    def parse(self, translation_import_queue_entry):
        """See `ITranslationFormatImporter`."""
        self.basepath = translation_import_queue_entry.path
        self.productseries = translation_import_queue_entry.productseries
        self.distroseries = translation_import_queue_entry.distroseries
        self.sourcepackagename = (
            translation_import_queue_entry.sourcepackagename)
        self.is_published = translation_import_queue_entry.is_published

        librarian_client = getUtility(ILibrarianClient)
        self.content = librarian_client.getFileByAlias(
            translation_import_queue_entry.content.id)

        parser = PoParser()
        return parser.parse(self.content.read())

    def getHeaderFromString(self, header_string):
        """See `ITranslationFormatImporter`."""
        return PoHeader(header_string)

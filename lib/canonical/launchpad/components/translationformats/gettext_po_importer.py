# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'TranslationFormatImporter'
    ]

from email.Utils import parseaddr
from zope.component import getUtility
from zope.interface import implements

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.interfaces import ITranslationFormatImporter
from canonical.launchpad.components.translationformats.gettext_po_parser import (
    POParser)
from canonical.librarian.interfaces import ILibrarianClient
from canonical.lp.dbschema import TranslationFileFormat


class TranslationFormatImporter:
    """Support class to import gettext .po files."""
    implements(ITranslationFormatImporter)

    def __init__(self, translation_import_queue_entry, logger=None):
        self.basepath = translation_import_queue_entry.path
        self.productseries = translation_import_queue_entry.productseries
        self.distroseries = translation_import_queue_entry.distroseries
        self.sourcepackagename = (
            translation_import_queue_entry.sourcepackagename)
        self.is_published = translation_import_queue_entry.is_published
        self.logger = logger

        librarian_client = getUtility(ILibrarianClient)
        self.content = librarian_client.getFileByAlias(
            translation_import_queue_entry.content.id)

        self._doParsing()

    def _doParsing(self):
        """Parse self.content content.

        Once the parse is done self.header and self.messages contained
        elements parsed.
        """
        parser = POParser()
        parser.write(self.content.read())
        parser.finish()

        self.header = parser.header
        self.messages = parser.messages

    @cachedproperty
    def format(self):
        """See ITranslationImporter."""
        return TranslationFileFormat.PO

    def canHandleFileExtension(self, extension):
        """See ITranslationImporter."""
        return extension in ['.po', '.pot']

    def getLastTranslator(self):
        """See ITranslationImporter."""
        if self.header is None:
            # The file does not have a header field.
            return (None, None)

        try:
            last_translator = self.header['Last-Translator']
        except KeyError:
            # Usually we should only get a KeyError exception but if we get
            # any other exception we should do the same, use the importer name
            # as the person who owns the imported po file.
            return (None, None)

        name, email = parseaddr(last_translator)

        if email == 'EMAIL@ADDRESS' or not '@' in email:
            # Gettext (and Rosetta) sets by default the email address to
            # EMAIL@ADDRESS unless we know the real address, thus, we know this
            # isn't a real account and we use the person that imported the file
            # as the owner.
            return None
        else:
            return (name, email)

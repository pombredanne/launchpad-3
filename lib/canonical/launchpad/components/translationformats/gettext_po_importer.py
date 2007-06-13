# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'GettextPoImporter'
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


class GettextPoImporter:
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

        Once the parse is done self.header and self.messages contain the
        elements parsed.
        """
        parser = POParser()
        parser.write(self.content.read())
        parser.finish()

        self.header = parser.header
        self.messages = parser.messages

    @cachedproperty
    def format(self):
        """See ITranslationFormatImporter."""
        return TranslationFileFormat.PO

    def canHandleFileExtension(self, extension):
        """See ITranslationFormatImporter."""
        return extension in ('.po', '.pot')

    def getLastTranslator(self):
        """See ITranslationFormatImporter."""
        if self.header is None:
            # The file does not have a header field.
            return None, None

        # Get last translator information. If it's not found, we use the
        # default value from Gettext.
        last_translator = self.header.get(
            'Last-Translator', 'FULL NAME <EMAIL@ADDRESS>')

        name, email = parseaddr(last_translator)

        if email == 'EMAIL@ADDRESS' or '@' not in email:
            # Gettext (and Launchpad) sets by default the email address to
            # EMAIL@ADDRESS unless it knows the real address, thus,
            # we know this isn't a real account so we don't accept it as a
            # valid one.
            return None, None
        else:
            return name, email

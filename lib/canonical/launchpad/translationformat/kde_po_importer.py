# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'KdePoImporter'
    ]

from email.Utils import parseaddr
from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import ITranslationFormatImporter
from canonical.launchpad.translationformat.gettext_po_parser import POParser
from canonical.launchpad.translationformat.gettext_po_importer import (
    GettextPoImporter)
from canonical.librarian.interfaces import ILibrarianClient
from canonical.lp.dbschema import TranslationFileFormat


class KdePoImporter(GettextPoImporter):
    """Support class to import KDE .po files."""
    implements(ITranslationFormatImporter)

    @property
    def format(self):
        """See `ITranslationFormatImporter`."""
        return TranslationFileFormat.KDEPO

    @property
    def content_type(self):
        """See `ITranslationFormatImporter`."""
        return 'application/x-po'

    def parse(self, translation_import_queue_entry):
        """See `ITranslationFormatImporter`."""
        GettextPoImporter.parse(self, translation_import_queue_entry)

        for message in self.messages:
            msgid = message.msgid
            if msgid.lower().startswith('_n: ') and '\n' in msgid:
                # This is a KDE plural form
                singular, plural = msgid[3:].split('\n')

                message.msgid = singular
                message.msgid_plural = plural
                message.msgstr_plurals = message.msgstr.split('\n')


    def getLastTranslator(self):
        """See `ITranslationFormatImporter`."""
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

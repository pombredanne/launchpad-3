# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'KdePoImporter'
    ]

from zope.interface import implements

from canonical.launchpad.interfaces import ITranslationFormatImporter
from canonical.launchpad.translationformat.gettext_po_parser import POParser
from canonical.launchpad.translationformat.gettext_po_importer import (
    GettextPoImporter)
from canonical.lp.dbschema import TranslationFileFormat


class KdePoImporter(GettextPoImporter):
    """Support class to import KDE .po files."""
    implements(ITranslationFormatImporter)

    def format(self, content):
        """See `ITranslationFormatImporter`."""
        parser = POParser()
        parser.write(content)
        parser.finish()
        for message in parser.messages:
            msgid = message.msgid
            if msgid.lower().startswith('_n: ') and '\n' in msgid:
                return TranslationFileFormat.KDEPO
        return TranslationFileFormat.PO

    @property
    def content_type(self):
        """See `ITranslationFormatImporter`."""
        return 'application/x-po'

    def parse(self, translation_import_queue_entry):
        """See `ITranslationFormatImporter`."""
        GettextPoImporter.parse(self, translation_import_queue_entry)

        for message in self.messages:
            msgid = message.msgid
            if msgid.lower().startswith('_n:') and '\n' in msgid:
                # This is a KDE plural form
                singular, plural = msgid[4:].split('\n')

                message.msgid = singular
                message.msgid_plural = plural
                message.msgstr_plurals = message.msgstr.split('\n')
                self.internal_format = TranslationFileFormat.KDEPO

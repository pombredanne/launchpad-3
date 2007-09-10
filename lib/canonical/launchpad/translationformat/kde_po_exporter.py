# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Export module for KDE legacy .po file format.

This is an extension of standard gettext PO files.
You can read more about this file format from:

 * http://l10n.kde.org/docs/translation-howto/gui-peculiarities.html
 * http://docs.kde.org/development/en/kdesdk/kbabel/kbabel-pluralforms.html
 * http://websvn.kde.org/branches/KDE/3.5/kdelibs/kdecore/klocale.cpp
"""

__metaclass__ = type

__all__ = [
    'KdePOExporter'
    ]

from zope.interface import implements

from canonical.launchpad.interfaces import ITranslationFormatExporter

from canonical.launchpad.translationformat.gettext_po_exporter import (
    GettextPOExporter)
from canonical.lp.dbschema import TranslationFileFormat

class KdePOExporter(GettextPOExporter):
    """Support class for exporting legacy KDE .po files."""
    implements(ITranslationFormatExporter)

    def __init__(self, context=None):
        # See GettextPOExporter.__init__ for explanation of `context`.
        self.format = TranslationFileFormat.KDEPO
        # We can also export TranslationFileFormat.PO, but the need for this
        # is very limited: only if we do a correct import, but don't mark this
        # as KDEPO inside potemplate.source_file_format, what would be a bug
        # in our code
        self.supported_formats = [ TranslationFileFormat.KDEPO ]

    def exportTranslationMessage(self, translation_message):
        """See `ITranslationFormatExporter`."""
        # Special handling of context and plural forms
        if translation_message.context is not None:
            # Lets turn context messages into legacy KDE context
            translation_message.msgid = (u"_: " + translation_message.context +
                                         "\n" + translation_message.msgid)
            translation_message.context = None
        elif translation_message.msgid_plural is not None:
            # Also, lets handle legacy KDE plural forms
            translations = translation_message.translations
            translation_message._translations = [
                "\n".join(translation_message.translations)]
            translation_message.msgid = (
                "_n: " + translation_message.msgid + "\n" +
                translation_message.msgid_plural)
            translation_message.msgid_plural = None

        return GettextPOExporter.exportTranslationMessage(
            self, translation_message)

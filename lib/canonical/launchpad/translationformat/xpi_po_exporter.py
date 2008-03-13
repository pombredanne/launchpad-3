# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0231
"""Export module for XPI files using .po file format."""

__metaclass__ = type

__all__ = [
    'XPIPOExporter'
    ]

from zope.interface import implements

from canonical.launchpad.interfaces import (
    ITranslationFormatExporter, TranslationFileFormat)

from canonical.launchpad.translationformat.gettext_po_exporter import (
    GettextPOExporter)


class XPIPOExporter(GettextPOExporter):
    """Support class for exporting XPI files as .po files."""
    implements(ITranslationFormatExporter)

    def __init__(self, context=None):
        # 'context' is ignored because it's only required by the way the
        # exporters are instantiated but it isn't used by this class.

        self.format = TranslationFileFormat.XPIPO
        # XPIPOExporter is also able to export `TranslationFileFormat.PO`,
        # but there is not much practical use for that, so we are not listing
        # it as one of the supported formats for this exporter.
        self.supported_source_formats = [TranslationFileFormat.XPI]

    def exportTranslationMessageData(self, translation_message):
        """See `ITranslationFormatExporter`."""
        # XPI file format uses singular_text and plural_text instead of
        # msgid_singular and msgid_plural.
        if translation_message.singular_text is not None:
            translation_message.msgid_singular = (
                translation_message.singular_text)
        if translation_message.plural_text is not None:
            translation_message.msgid_plural = translation_message.plural_text
        return GettextPOExporter.exportTranslationMessageData(
            self, translation_message)

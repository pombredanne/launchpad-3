# Copyright 2007 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute
from zope.schema import Choice

__metaclass__ = type

__all__ = [
    'IExportedTranslationFile',
    'ITranslationExporter',
    'ITranslationFormatExporter',
    'UnknownTranslationExporterError',
    ]


class UnknownTranslationExporterError(Exception):
    """Something unkown went wrong while doing an export."""


class ITranslationExporter(Interface):
    """Exporter for translation files."""

    def getTranslationFormatExportersForFileFormat(file_format):
        """Return all ITranslationFormatExporter that can export file_format.

        :param file_format: An ITranslationFileFormat entry we want to export
            from.
        """

    def getTranslationFormatExporterByFileFormat(file_format):
        """Return the ITranslationFormatExporter that generates file_format.

        :param file_format: An ITranslationFileFormat entry that we want to
            get its exporter class.
        :return: None if there is no handler for that file format.
        """


class ITranslationFormatExporter(Interface):
    """Translation file format exporter."""

    format = Choice(
        title=u'The file format that will be used for the export.',
        vocabulary='TranslationFileFormat',
        required=True, readonly=True)

    handable_formats = Attribute(
        "List of TranslationFileFormat entries that this exporter is able"
        " to convert from.")

    def exportTranslationMessage(translation_message):
        """Return a unicode string representing translation_message.

        :arg translation_message: ITranslationMessage to export.
        :return: Unicode string representing given ITranslationMessage.
        """

    def exportTranslationFiles(translation_file_list, ignore_obsolete=False,
                               force_utf8=False):
        """Return an IExportedTranslationFile representing the export.

        :param translation_file_list: A list of ITranslationFile objects to
            export.
        :param ignore_obsolete: Whether obsolete messages should not be
            exported.
        :param force_utf8: Whether the export should be forced to use UTF-8
            encoding. This argument is only useful if the file format allows
            different encodings.
        :return: An IExportedTranslationFile representing the export.
        """


class IExportedTranslationFile(Interface):
    """Exported translation file data."""

    content_type = Attribute("Content type string for this file format.")

    content_file = Attribute("File like object with the exported content.")

    path = Attribute("Relative file path for this exported file.")

    file_extension = Attribute(
        "File extension for this exported translation file.")

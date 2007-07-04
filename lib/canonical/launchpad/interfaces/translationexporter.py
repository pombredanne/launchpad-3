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
        :return: None if there are no exporters for that file format.
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

    def exportTranslationFiles(translation_file_list):
        """Return file path and file like object with given list serialized.

        :param translation_file_list: A list of ITranslationFile objects to
            export.
        :return: A tuple with a string noting the exported file path and a
            file like object with 'translation_file_list' serialized. File
            path would be None if the exporter cannot figure a value.
        """


class IExportedTranslationFile(Interface):
    """Exported translation file data."""

    content_type = Attribute("Content type string for this file format.")

    path = Attribute("Relative file path for this exported file.")

    content_file = Attribute("File like object with the exported content.")

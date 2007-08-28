# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Interfaces to handle translation files exports."""

from zope.interface import Interface
from zope.schema import Choice, List, TextLine, Object

__metaclass__ = type

__all__ = [
    'IExportedTranslationFile',
    'ITranslationExporter',
    'ITranslationFormatExporter',
    'UnknownTranslationExporterError',
    ]


class UnknownTranslationExporterError(Exception):
    """Something unknown went wrong while doing an export."""


class ITranslationExporter(Interface):
    """Exporter for translation files."""

    def getTranslationFormatExportersForFileFormat(file_format):
        """Return all `ITranslationFormatExporter` that can export file_format.

        :param file_format: The source `ITranslationFileFormat` format for the
            translation file we want to export.
        :return: A list of `ITranslationFormatExporter` objects that are able
            to handle exports for translation files that have file_format
            as their source format.
        """

    def getTranslationFormatExporterByFileFormat(file_format):
        """Return the ITranslationFormatExporter that generates file_format.

        :param file_format: An ITranslationFileFormat entry that we want to
            get its exporter class.
        :return: An `ITranslationFormatExporter` object that handles
            file_format exports or None if there is no handler available for
            it.
        """


class ITranslationFormatExporter(Interface):
    """Translation file format exporter."""

    format = Choice(
        title=u'The file format that the translation will be exported to.',
        vocabulary='TranslationFileFormat',
        required=True, readonly=True)

    supported_formats = List(
        title=u'TranslationFileFormat entries supported',
        description=u'''
            TranslationFileFormat entries supported that this exporter is able
            to convert from.
            ''',
        required=True, readonly=True)

    def exportTranslationMessage(translation_message):
        """Export the string for the given translation message.

        :param translation_message: ITranslationMessage to export.
        :return: Unicode string representing given ITranslationMessage.
        """

    def exportTranslationFiles(translation_file_list, ignore_obsolete=False,
                               force_utf8=False):
        """Return an IExportedTranslationFile representing the export.

        :param translation_file_list: A list of ITranslationFile objects to
            export.
        :param ignore_obsolete: A flag indicating whether obsolete messages
            should be exported.
        :param force_utf8: A flag indicating whether the export should be
            forced to use UTF-8 encoding. This argument is only useful if the
            file format allows different encodings.
        :return: An IExportedTranslationFile representing the export.
        """


class IExportedTranslationFile(Interface):
    """Exported translation file data."""

    content_type = TextLine(
        title=u'Content type string for this file format.',
        required=True, readonly=True)

    content_file = Object(
        title=u'File like object with the exported content.',
        required=True, readonly=True)

    path = TextLine(
        title=u'Relative file path for this exported file.',
        required=True, readonly=True)

    file_extension = TextLine(
        title=u'File extension for this exported translation file.',
        required=True, readonly=True)

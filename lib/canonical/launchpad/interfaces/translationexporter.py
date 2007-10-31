# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces to handle translation files exports."""

__metaclass__ = type

__all__ = [
    'IExportedTranslationFile',
    'ITranslationExporter',
    'ITranslationFormatExporter',
    'UnknownTranslationExporterError',
    ]

from zope.interface import Interface
from zope.schema import Choice, Int, List, TextLine

from canonical.launchpad import _
from canonical.launchpad.interfaces.translationfileformat import (
    TranslationFileFormat)
from canonical.launchpad.interfaces.translationcommonformat import (
    TranslationImportExportBaseException)


class UnknownTranslationExporterError(TranslationImportExportBaseException):
    """Something unknown went wrong while doing an export."""


class ITranslationExporter(Interface):
    """Exporter for translation files."""

    def getExportersForSupportedFileFormat(file_format):
        """Return all `ITranslationFormatExporter` that can export file_format.

        :param file_format: The source `ITranslationFileFormat` format for the
            translation file we want to export.
        :return: A list of `ITranslationFormatExporter` objects that are able
            to handle exports for translation files that have file_format
            as their source format.
        """

    def getExporterProducingTargetFileFormat(file_format):
        """Return the `ITranslationFormatExporter` that generates file_format.

        :param file_format: An `ITranslationFileFormat` entry that we want to
            get its exporter class.
        :return: An `ITranslationFormatExporter` object that handles
            file_format exports or None if there is no handler available for
            it.
        """


class ITranslationFormatExporter(Interface):
    """Translation file format exporter."""

    # XXX CarlosPerelloMarin 20070905: This should be moved to use the new
    # Enum infrastructure. See bug #135853 for more information.
    format = Choice(
        title=_('The file format that the translation will be exported to.'),
        vocabulary=TranslationFileFormat,
        required=True, readonly=True)

    supported_source_formats = List(
        title=_('TranslationFileFormat entries supported'),
        description=_('''
            TranslationFileFormat entries supported that this exporter is able
            to convert from.
            '''),
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
        title=_('Content type string for this file format.'),
        required=True, readonly=True)

    path = TextLine(
        title=_('Relative file path for this exported file.'),
        required=True, readonly=True)

    file_extension = TextLine(
        title=_('File extension for this exported translation file.'),
        required=True, readonly=True)

    size = Int(title=_('Size of the file.'), required=True, readonly=True)

    def read(size=None):
        """Read at most size bytes from the file.

        :param size: Size of the read buffer. If the size  argument is
            negative or omitted, read all data until EOF is reached.

        :raises ValueError: If the file is closed.
        """

    def close():
        """Close the file.

        A closed file cannot be read any more. Calling close() more than once
        is allowed.
        """

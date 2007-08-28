# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

"""Interfaces to handle translation files imports."""

from zope.interface import Interface
from zope.schema import Bool, Choice, List, TextLine

__metaclass__ = type

__all__ = [
    'ITranslationFormatImporter',
    'ITranslationImporter',
    'OldTranslationImported',
    'NotExportedFromLaunchpad',
    'TranslationFormatSyntaxError',
    'TranslationFormatInvalidInputError',
    ]


class OldTranslationImported(Exception):
    """A newer file has already been imported."""


class NotExportedFromLaunchpad(Exception):
    """An imported file lacks the Launchpad export time."""


class TranslationFormatBaseError(Exception):
    """Base exception for errors in translation format files."""

    def __init__(self, filename='unknown', line_number=None, message=None):
        """Initialise the exception information.

        :param filename: The file name that is being parsed.
        :param line_number: The line number where the error was found.
        :param message: The concrete syntax error found.
        """
        assert filename is not None, 'filename cannot be None'

        self.filename = filename
        self.line_number = line_number
        self.message = message


class TranslationFormatSyntaxError(TranslationFormatBaseError):
    """A syntax error occurred while parsing a translation file."""

    def __str__(self):
        if self.message is not None:
            return self.message
        if self.line_number is None:
            return '%s: syntax error on an unknown line' % self.filename
        else:
            return '%s: syntax error on entry at line %d' % (
                self.filename, self.line_number)


class TranslationFormatInvalidInputError(TranslationFormatBaseError):
    """Some fields in the parsed file contain bad content."""

    def __str__(self):
        if self.message is not None:
            return self.message
        if self.line_number is None:
            return '%s: invalid input on an unknown line' % self.filename
        else:
            return '%s: invalid input on entry at line %d' % (
                self.filename, self.line_number)


class ITranslationImporter(Interface):
    """Importer of translation files."""

    file_extensions_with_importer = List(
        title=u'List of file extensions we have imports for.',
        required=True, readonly=True)

    def getTranslationFileFormatByFileExtension(file_extension):
        """Return the translation file format for given file_extension.

        :param file_extension: File extension.
        :return: None if there is no handler for that file_extension.
        """

    def getTranslationFormatImporter(file_format):
        """Return the translation file format for give file_format.

        :param file_format: A TranslationFileFormat entry.
        :return: None if there is no handler for that file_format.
        """

    def importFile(translation_import_queue_entry):
        """Convert a translation resource into database objects.

        :param translation_import_queue_entry: An ITranslationImportQueueEntry
            entry.

        :raise OldTranslationImported: If the entry is older than the
            previously imported file.
        :raise NotExportedFromLaunchpad: If the entry imported is not
            published and doesn't have the tag added by Launchpad on export
            time.

        :return: a list of dictionaries with three keys:
            - 'pomsgset': The database pomsgset with an error.
            - 'pomessage': The original POMessage object.
            - 'error-message': The error message as gettext names it.
        """


class ITranslationFormatImporter(Interface):
    """Translation file format importer."""

    format = Choice(
        title=u'The file format of the import.',
        vocabulary='TranslationFileFormat',
        required=True)

    content_type = TextLine(
        title=u'Content type string for this file format.',
        required=True, readonly=True)

    file_extensions = List(
        title=u'File extensions handable by this importer.',
        required=True, readonly=True)

    has_alternative_msgid = Bool(
        title=u'A flag indicating whether uses ids to identify strings',
        description=u'''
            A flag indicating whether this file format importer uses ids to
            identify strings instead of English strings.
            ''',
        required=True, readonly=True)

    def parse(translation_import_queue_entry):
        """Parse given translation_import_queue_entry object.

        :param translation_import_queue: An ITranslationImportQueueEntry to
            import.
        :return: an ITranslationFile representing the parsed file.
        """

    def getHeaderFromString(header_string):
        """Return an ITranslationHeader representing the given header_string.

        :param header_string: A text representing a string for this concrete
            file format.
        """

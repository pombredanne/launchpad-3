# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute
from zope.interface.common.mapping import IMapping
from zope.schema import Choice, Field

__metaclass__ = type

__all__ = [
    'ITranslationFormatImporter',
    'ITranslationHeader',
    'ITranslationImporter',
    'ITranslationMessage',
    'OldTranslationImported',
    'NotExportedFromLaunchpad',
    'TranslationFormatSyntaxError',
    'TranslationFormatInvalidInputError',
    'UnknownTranslationRevisionDate',
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


class UnknownTranslationRevisionDate(Exception):
    """Unknown revision date for translation resource."""


class ITranslationImporter(Interface):
    """Importer of translation files."""

    file_extensions_with_importer = Attribute(
        "List of file extension we have imports for.")

    def getContentTypeByFileExtension(file_extension):
        """Return content type for given file_extension.

        If file_extension cannot be handled, return None.
        """

    def getTranslationFileFormatByFileExtension(file_extension):
        """Return the translation file format for given file_extension.

        If file_extension cannot be handled, return None.
        """

    def hasAlternativeMsgID(file_format):
        """Whether the given format uses alternative msgid instead of English.

        :arg file_format: a TranslationFileFormat value.
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

    content_type = Attribute(
        "Content type string for this file format.")

    file_extensions = Attribute(
        "Set of file extensions handlable by this importer.")

    header = Attribute("An ITranslationHeader for the parsed file.")

    messages = Attribute(
        "The list of ITranslationMessage included in the parsed file.")

    has_alternative_msgid = Attribute("""
        Whether this file format importer uses ids to identify strings
        instead of English strings.""")

    def parse(translation_import_queue_entry):
        """Parse given translation_import_queue_entry object.

        :arg translation_import_queue: An ITranslationImportQueueEntry to
            import.

        Once the parse is done self.header and self.messages contain the
        elements parsed.
        """

    def canHandleFileExtension(extension):
        """Whether this importer is able to handle the given file extension.

        :param extension: File extension (starting with '.').
        """

    def getLastTranslator():
        """Return a tuple of name and email for last translator.

        name and/or email would be None if there is no such information.
        """


class ITranslationHeader(IMapping):
    """Translation header interface."""

    messages = Attribute('''
        A reference to the sequence of ITranslationMessage this header
        refers to
        ''')

    def getTranslationRevisionDate():
        """Return when the translation resource was last revised.

        The returned object is a datetime object.

        Raises UnknownTranslationRevisionDate exception if the information is
        unavailable  or invalid.
        """

    def getLaunchpadExportDate():
        """Return when this file was last exported from Launchpad or None.

        The returned object is a datetime object.
        """

    def getPluralFormExpression():
        """Return the plural form expression defined in the file or None."""

    def getRawContent():
        """Return the header as found in the file."""


class ITranslationMessage(Interface):
    """Translation message interface."""

    msgid = Attribute(
        "The msgid of the message (as unicode).")

    msgid_plural = Attribute(
        "The plural msgid of the message (as unicode) or None.")

    translations = Attribute(
        "The translations of the message (as a list of unicodes).")

    comment = Attribute(
        "The human-written comments ('# foo') of the message (as unicode).")

    source_comment = Attribute(
        "The parser-generated comments ('#. foo') of the message (as unicode)."
        )

    file_references = Attribute(
        "The references ('#: foo') of the message (as unicode).")

    flags = Attribute(
        "The flags of the message (a Set of strings).")

    obsolete = Attribute(
        'True if message is obsolete (#~ msgid "foo"\\n#~ msgstr "bar").')

    nplurals = Attribute(
        """The number of plural forms for this language, as used in this file.
        None means the header does not have a Plural-Forms entry.""")

    pluralExpr = Attribute(
        "The expression used to get a plural form from a number.")

    def flagsText(flags=None):
        """The flags of the message.

        if a sequence or set is passed in, pretend these are the messages
        flags and return a unicode representing them.
        """

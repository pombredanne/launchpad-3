# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute
from zope.interface.common.mapping import IMapping
from zope.schema import Choice

from canonical.lp.dbschema import TranslationFileFormat

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
    """Raised when we have a newer file already imported."""


class NotExportedFromLaunchpad(Exception):
    """Raised when a file imported lacks the export time from Launchpad."""


class TranslationFormatBaseError(Exception):
    """Base exception for errors in translation format files."""

    def __init__(self, filename='unknown', line_number=None, message=None):
        """Initialise the exception information.

        :arg filename: The file name that is being parsed.
        :arg line_number: The line number where the error was found.
        :arg message: The concrete syntax error found.
        """
        assert filename is not None, 'filename cannot be None'

        self.filename = filename
        self.line_number = line_number
        self.message = message


class TranslationFormatSyntaxError(TranslationFormatBaseError):
    """Raised when there is a syntax error while parsing a file."""

    def __str__(self):
        if self.message is not None:
            return self.message
        if self.line_number is None:
            return '%s: syntax error on an unknown line' % self.filename
        else:
            return '%s: syntax error on entry at line %d' % (
                self.filename, self.line_number)


class TranslationFormatInvalidInputError(TranslationFormatBaseError):
    """Raised when there is bad content is some fields of the parsed file."""

    def __str__(self):
        if self.message is not None:
            return self.message
        if self.line_number is None:
            return '%s: invalid input on an unknown line' % self.filename
        else:
            return '%s: invalid input on entry at line %d' % (
                self.filename, self.line_number)


class UnknownTranslationRevisionDate(Exception):
    """Raised when don't know the revision date for a translation resource."""


class ITranslationImporter(Interface):
    """Interface to implement a component that handles translation imports."""

    def import_file(translation_import_queue_entry, logger=None):
        """Convert a translation resource into DB objects.

        :arg translation_import_queue_entry: An ITranslationImportQueueEntry
            entry.
        :arg logger: A logger object or None.

        If the entry is older than previous imported file,
        OldTranslationImported exception is raised.

        If the entry imported is not published and doesn't have the tag added
        by Launchpad on export time, NotExportedFromLaunchpad exception is
        raised.

        Return a list of dictionaries with three keys:
            - 'pomsgset': The DB pomsgset with an error.
            - 'pomessage': The original POMessage object.
            - 'error-message': The error message as gettext names it.
        """


class ITranslationFormatImporter(Interface):
    """Translation file format importer."""

    format = Choice(
        title=u'The file format of the import.',
        values=TranslationFileFormat.items,
        required=True)
    header = Attribute("An ITranslationHeader for the parsed file.")
    messages = Attribute(
        "The list of ITranslationMessage included in the parsed file.")

    def canHandleFileExtension(extension):
        """Whether this importer is able to handle the given file extension.

        :arg extension: File extension (starting with '.').
        """

    def getLastTranslator():
        """Return a tuple of name and email for last translator.

        name and/or email would be None if there is no such information.
        """


class ITranslationHeader(IMapping):
    """Translation header interface."""

    messages = Attribute(
        "A reference to the sequence of ITranslationMessage this header"
        " refers to")

    def getTranslationRevisionDate():
        """Return datetime object when was last touched translation resource.

        Raises UnknownTranslationRevisionDate exception if the information is
        not valid or available.
        """

    def getLaunchpadExportDate():
        """Return datetime object when this file was exported from Launchpad.

        If it was not exported from Launchpad, return None.
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
        "The plural msgid of the message (as unicode), if present.")
    msgstr = Attribute(
        "The msgstr of the message (as unicode).")
    msgstrPlurals = Attribute(
        "The msgstr's of the message, if more than one (as a list of unicodes).")
    comment = Attribute(
        "The human-written comments ('# foo') of the message (as unicode).")
    source_comment = Attribute(
        "The parser-generated comments ('#. foo') of the message (as unicode).")
    file_references = Attribute(
        "The references ('#: foo') of the message (as unicode).")
    flags = Attribute(
        "The flags of the message (a Set of strings).")
    obsolete = Attribute(
        """True if message is obsolete (#~ msgid "foo"\\n#~ msgstr "bar").""")
    nplurals = Attribute(
        """The number of plural forms for this language, as used in this file.
        None means the header does not have a Plural-Forms entry.""")
    pluralExpr = Attribute(
        """The expression used to get a plural form from a number.""")

    def flagsText(flags=None):
        """The flags of the message, as unicode; or, if a sequence
        or set is passed in, pretend these are the messages flags and
        return a unicode representing them"""


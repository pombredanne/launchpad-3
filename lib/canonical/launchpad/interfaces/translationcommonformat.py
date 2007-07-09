# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute
from zope.interface.common.mapping import IMapping

__metaclass__ = type

__all__ = [
    'ITranslationFile',
    'ITranslationHeader',
    'ITranslationMessage',
    ]


class ITranslationFile(Interface):
    """Parsed translation template file interface."""

    header = Attribute("An ITranslationHeader for the parsed file.")

    messages = Attribute(
        "The list of ITranslationMessage included in the parsed file.")

    path = Attribute("The path directory where this file is stored.")

    translation_domain = Attribute(
        "Translation domain used for this template. It would be used to"
        " find its content on the file system, when its associated"
        " application is executed.")

    is_template = Attribute(
        "Whether this entry is a template without translations.")

    language_code = Attribute(
        "Language iso code for this translations or None either if it's"
        " unknown or is_template flag is set.")


class ITranslationHeader(IMapping):
    """Translation header interface."""

    is_fuzzy = Attribute(
        "Whether the header needs some field changes before it's useful.")

    template_creation_date = Attribute(
        "A datetime object representing when was created the template used in"
        " this file.")

    translation_revision_date = Attribute(
        "A datetime object for when the translation resource was last"
        " revised or None.")

    last_translator = Attribute(
        "String noting the last person doing translations in this file.")

    language_team = Attribute(
        "String noting the language team in charge of this translation.")

    has_plural_forms = Attribute("Whether this file contains plural forms.")

    number_plural_forms = Attribute("Number of plural forms.")

    plural_form_expression = Attribute(
        "The plural form expression defined in this file or None.")

    charset = Attribute(
        "Charset used to encode the content in its native form.")

    launchpad_export_date = Attribute(
        "A datetime object for when this file was last exported from"
        " Launchpad or None.")

    comment = Attribute(
        "Header comment, it usually has copyright information and list of"
        " contributors.")

    def getRawContent():
        """Return header raw content in its native file format."""

    def updateFromTemplateHeader(template_header):
        """Update header with some content from the given template header.

        :param template_header: An ITranslationHeader for an IPOTemplate.

        The fields copied depend on the file format.
        """

    def getLastTranslator():
        """Return a tuple of name and email for last translator.

        name and/or email would be None if there is no such information.
        """

    def setLastTranslator(email, name=None):
        """Set last translator information.

        :param email: A string with the email address for last translator.
        :param name: The name for the last translator or None.
        """


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

    is_obsolete = Attribute(
        'Whether the message is obsolete and not used anymore.')

    nplurals = Attribute(
        """The number of plural forms for this language, as used in this file.
        None means the header does not have a Plural-Forms entry.""")

    pluralExpr = Attribute(
        "The expression used to get a plural form from a number.")

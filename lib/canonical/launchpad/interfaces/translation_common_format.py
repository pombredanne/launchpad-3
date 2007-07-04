# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

from zope.interface import Interface, Attribute
from zope.interface.common.mapping import IMapping
from zope.schema import Choice

__metaclass__ = type

__all__ = [
    'ITranslationFile',
    'ITranslationHeader',
    'ITranslationMessage',
    'ITranslationTemplateFile',
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

    def updateFromTemplateHeader(template_header):
        """Update this class information based on the given template one.

        :param template_header: an ITranslationHeader representing a template
            header.

        The concrete fields updated depend on the file format that implements
        this interface.
        """

    def setTranslationRevisionDate(revision_date):
        """Store when was last touched a translation.

        :param revision_date: a datetime object.
        """

    def setPluralFormFields(number_plural_forms=None,
                            plural_form_expression=None):
        """Store given plural form information.

        :param number_plural_forms: Amount of plural forms.
        :param plural_form_expression: A string representing how to use plural
            forms following Gettext's definition. You can see more about it at
            http://www.gnu.org/software/gettext/manual/html_node/Plural-forms.html

        Either both are None or not None, but we cannot get a mix.
        """

    def setExportDateField(export_date):
        """Store the date when this export is being done.

        :param export_date: a datetime object.
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

# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Interfaces for efficient translation file exports."""

__metaclass__ = type

__all__ = [
    'IVPOExportSet',
    'IVPOExport',
    ]

from zope.interface import Interface
from zope.schema import Bool, Int, Object, Text

from canonical.launchpad import _
from canonical.launchpad.interfaces.language import ILanguage
from canonical.launchpad.interfaces.pofile import IPOFile
from canonical.launchpad.interfaces.potemplate import IPOTemplate


class IVPOExportSet(Interface):
    """A collection of IVPOExport-providing rows."""

    def get_pofile_rows(pofile):
        """Return all rows which belong to the given PO file."""

    def get_potemplate_rows(potemplate):
        """Return all rows which belong to a particular PO template."""

    def get_distroseries_pofiles(series, date=None, component=None,
        languagepack=None):
        """Get a list of PO files which would be contained in an export of a
        distribution series.

        The filtering is done based on the 'series', last modified 'date',
        archive 'component' and if it belongs to a 'languagepack'
        """

    def get_distroseries_pofiles_count(series, date=None, component=None,
        languagepack=None):
        """Return the number of PO files which would be contained in an export
        of a distribution series.

        The filtering is done based on the 'series', last modified 'date',
        archive 'component' and if it belongs to a 'languagepack'
        """

    def get_distroseries_potemplates(series, component=None,
        languagepack=None):
        """Get a list of PO files which would be contained in an export of a
        distribution series.

        The filtering is done based on the 'series', last modified 'date',
        archive 'component' and if it belongs to a 'languagepack'
        """

    def get_distroseries_rows(series, date=None):
        """Return all rows which belong to a particular distribution
        series.
        """


class IVPOExport(Interface):
    """Database view for efficient PO exports."""

    potemplate = Object(
        title=u"See `IPOTemplate`",
        required=True, readonly=True, schema=IPOTemplate)

    template_header = Text(
        title=u"See `IPOTemplate`.header",
        required=True, readonly=True)

    pofile = Object(
        title=u"See `IPOFile`",
        required=True, readonly=True, schema=IPOFile)

    language = Object(
        title=u"See `ILanguage`",
        required=True, readonly=True, schema=ILanguage)

    variant = Text(
        title=u"See IPOFile.variant",
        required=False, readonly=True)

    translation_file_comment = Text(
        title=u"See IPOFile.topcomment",
        required=False, readonly=True)

    translation_header = Text(
        title=u"See IPOFile.header",
        required=True, readonly=True)

    is_translation_header_fuzzy = Bool(
        title=u"See IPOFile.fuzzyheader",
        required=True, readonly=True)

    sequence = Int(
        title=u"See IPOTMsgSet.sequence",
        required=True, readonly=True)

    comment = Text(
        title=u"See IPOTMsgSet.commenttext",
        required=False, readonly=True)

    source_comment = Text(
        title=u"See IPOTMsgSet.sourcecomment",
        required=False, readonly=True)

    file_references = Text(
        title=u"See IPOTMsgSet.filereferences",
        required=False, readonly=True)

    flags_comment = Text(
        title=u"See IPOTMsgSet.flagscomment",
        required=False, readonly=True)

    context = Text(
        title=u"See IPOTMsgSet.context", readonly=True, required=False)

    msgid_singular = Text(
        title=u"See `IPOMsgID`.pomsgid",
        required=True, readonly=True)

    msgid_plural = Text(
        title=u"See `IPOMsgID`.pomsgid",
        required=False, readonly=True)

    is_fuzzy = Bool(
        title=u"See ITranslationMessage.is_fuzzy",
        readonly=True, required=False)

    is_current = Bool(
        title=_("Whether this message is currently used in Launchpad"),
        readonly=True, required=True)

    is_imported = Bool(
        title=_("Whether this message was imported"),
        readonly=True, required=True)

    translation0 = Text(
        title=u"See ITranslationMessage.msgstr0",
        readonly=True, required=False)

    translation1 = Text(
        title=u"See ITranslationMessage.msgstr1",
        readonly=True, required=False)

    translation2 = Text(
        title=u"See ITranslationMessage.msgstr2",
        readonly=True, required=False)

    translation3 = Text(
        title=u"See ITranslationMessage.msgstr3",
        readonly=True, required=False)

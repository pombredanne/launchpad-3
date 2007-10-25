# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces for efficient PO file exports."""

__metaclass__ = type

__all__ = ('IVPOExportSet', 'IVPOExport')

from zope.interface import Interface, Attribute
from zope.schema import Bool, Text

from canonical.launchpad import _


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

    name = Text(
        title=u"See IPOTemplate.name",
        readonly=True, required=True)

    translation_domain = Text(
        title=u"See IPOTemplate.translation_domain",
        readonly=True, required=True)

    potemplate = Attribute("See IPOTemplate")
    distroseries = Attribute("See IPOTemplate.distroseries")
    sourcepackagename = Attribute("See IPOTemplate.sourcepackagename")
    productseries = Attribute("See IPOTemplate.productseries")
    potheader = Attribute("See IPOTemplate.header")
    languagepack = Attribute("See IPOTemplate.languagepack")

    pofile = Attribute("See IPOFile")
    language = Attribute("See IPOFile.language")
    variant = Attribute("See IPOFile.variant")
    potopcomment = Attribute("See IPOFile.topcomment")
    poheader = Attribute("See IPOFile.header")
    pofuzzyheader = Attribute("See IPOFile.fuzzyheader")
    popluralforms = Attribute("See IPOFile.pluralforms")

    potmsgset = Attribute("See IPOTMsgSet.id")
    potsequence = Attribute("See IPOTMsgSet.sequence")
    potcommenttext = Attribute("See IPOTMsgSet.commenttext")
    sourcecomment = Attribute("See IPOTMsgSet.sourcecomment")
    flagscomment = Attribute("See IPOTMsgSet.flagscomment")
    filereferences = Attribute("See IPOTMsgSet.filereferences")

    current_translation = Attribute(_("See ITranslationMessage.id"))

    was_obsolete_in_last_import = Bool(
        title=u"See ITranslationMessage.was_obsolete_in_last_import",
        readonly=True, required=False)

    was_fuzzy_in_last_import = Bool(
        title=u"See ITranslationMessage.was_fuzzy_in_last_import",
        readonly=True, required=False)

    is_fuzzy = Bool(
        title=u"See ITranslationMessage.is_fuzzy",
        readonly=True, required=False)

    pocommenttext = Text(
        title=u"See ITranslationMessage.comment_text",
        readonly=True, required=False)

    msgstr0 = Text(
        title=u"See ITranslationMessage.msgstr0",
        readonly=True, required=False)
    msgstr1 = Text(
        title=u"See ITranslationMessage.msgstr1",
        readonly=True, required=False)
    msgstr2 = Text(
        title=u"See ITranslationMessage.msgstr2",
        readonly=True, required=False)
    msgstr3 = Text(
        title=u"See ITranslationMessage.msgstr3",
        readonly=True, required=False)

    msgid_singular = Attribute(_("Message identifier in singular form"))
    msgid_plural = Attribute(_("Message identifier in singular form"))

    context = Text(
        title=u"See IPOTMsgSet.context", readonly=True, required=False)

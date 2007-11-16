# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces for efficient PO file exports."""

__metaclass__ = type

__all__ = ('IVPOExportSet', 'IVPOExport')

from zope.interface import Interface, Attribute

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

    name = Attribute("See IPOTemplateName.name")
    translationdomain = Attribute("See IPOTemplateName.translationdomain")

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

    pomsgset = Attribute("See IPOMsgSet.id")
    posequence = Attribute("See IPOMsgSet.sequence")
    iscomplete = Attribute("See IPOMsgSet.iscomplete")
    obsolete = Attribute("See IPOMsgSet.obsolete")
    isfuzzy = Attribute("See IPOMsgSet.isfuzzy")
    pocommenttext = Attribute("See IPOMsgSet.commenttext")

    msgidpluralform = Attribute("See IPOMsgIDSighting.pluralform")

    translationpluralform = Attribute("See IPOSubmission.pluralform")
    activesubmission = Attribute(
        "See IPOSubmission.id and IPOSubmission.active")

    context = Attribute("See IPOTMsgSet.context")
    msgid = Attribute("See IPOMsgID.pomsgid")

    translation = Attribute("See IPOTranslation.translation")



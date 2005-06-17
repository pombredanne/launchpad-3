# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces for efficient PO file exports."""

__metaclass__ = type

__all__ = ('IVPOExportSet', 'IVPOExport')

from zope.interface import Interface, Attribute


class IVPOExport(Interface):
    """Database view for efficient PO exports."""

    name = Attribute("See IPOTemplateName.name")
    translationdomain = Attribute("See IPOTemplateName.translationdomain")

    potemplate = Attribute("See IPOTemplate.id")
    distrorelease = Attribute("See IPOTemplate.distrorelease")
    sourcepackagename = Attribute("See IPOTemplate.sourcepackagename")
    productrelease = Attribute("See IPOTemplate.productrelease")
    potheader = Attribute("See IPOTemplate.header")
    languagepack = Attribute("See IPOTemplate.languagepack")

    pofile = Attribute("See IPOFile.id")
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

    translationpluralform = Attribute("See IPOSelection.pluralform")
    activesubmission = Attribute("See IPOSelection.activesubmission")

    msgid = Attribute("See IPOMsgID.pomsgid")

    translation = Attribute("See IPOTranslation.translation")


class IVPOExportSet(Interface):
    """A collection of IVPOExport-providing rows."""

    def get_pofile_rows(potemplate, language, variant=None):
        """Return all rows which belong to a particular PO file."""

    def get_potemplate_rows(potemplate):
        """Return all rows which belong to a particular PO template."""

    def get_distrorelease_rows(potemplate):
        """Return all rows which belong to a particular distribution
        release.
        """



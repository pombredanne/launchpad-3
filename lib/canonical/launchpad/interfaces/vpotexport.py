# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Interfaces for efficient POT file exports."""

__metaclass__ = type

__all__ = ('IVPOTExportSet', 'IVPOTExport')

from zope.interface import Interface, Attribute

from canonical.launchpad import _


class IVPOTExportSet(Interface):
    """A collection of IVPOTExport-providing rows."""

    def get_potemplate_rows(potemplate):
        """Return all rows which belong to a particular PO template."""


class IVPOTExport(Interface):
    """Database view for efficient POT exports."""

    name = String(_("See `IPOTemplate.name`"))
    translation_domain = String(_("See `IPOTemplate.translationdomain`"))

    potemplate = Attribute("See IPOTemplate")
    distroseries = Attribute("See IPOTemplate.distroseries")
    sourcepackagename = Attribute("See IPOTemplate.sourcepackagename")
    productseries = Attribute("See IPOTemplate.productseries")
    header = Attribute("See IPOTemplate.header")
    languagepack = Attribute("See IPOTemplate.languagepack")

    potmsgset = Attribute("See IPOTMsgSet.id")
    sequence = Integer("See IPOTMsgSet.sequence")
    comment_text = Text("See `IPOTMsgSet.commenttext`")
    sourcecomment = Attribute("See IPOTMsgSet.sourcecomment")
    flagscomment = Attribute("See IPOTMsgSet.flagscomment")
    filereferences = Attribute("See IPOTMsgSet.filereferences")

    comment_text = Attribute(_("See `ITranslationMessage.commenttext`"))

    context = String(_("See `IPOTMsgSet.context`"))
    msgid = Attribute("See IPOMsgID.pomsgid")

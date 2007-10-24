# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Interfaces for efficient POT file exports."""

__metaclass__ = type

__all__ = ('IVPOTExportSet', 'IVPOTExport')

from zope.interface import Interface, Attribute
from zope.schema import Int, Text

from canonical.launchpad import _


class IVPOTExportSet(Interface):
    """A collection of IVPOTExport-providing rows."""

    def get_potemplate_rows(potemplate):
        """Return all rows which belong to a particular PO template."""


class IVPOTExport(Interface):
    """Database view for efficient POT exports."""

    name = Text(
        title=u"See `IPOTemplate`.name",
        required=True, readonly=True)

    translation_domain = Text(
        title=u"See `IPOTemplate`.translationdomain",
        required=True, readonly=True)

    potemplate = Attribute("See IPOTemplate")
    distroseries = Attribute("See IPOTemplate.distroseries")
    sourcepackagename = Attribute("See IPOTemplate.sourcepackagename")
    productseries = Attribute("See IPOTemplate.productseries")
    header = Attribute("See IPOTemplate.header")
    languagepack = Attribute("See IPOTemplate.languagepack")

    potmsgset = Attribute(_("See `IPOTMsgSet.id`"))

    sequence = Int(
        title=u"See `IPOTMsgSet`.sequence",
        required=False, readonly=True)

    comment_text = Text(
        title=u"See `IPOTMsgSet`.commenttext",
        required=False, readonly=True)

    source_comment = Text(
        title=u"See `IPOTMsgSet`.sourcecomment",
        required=False, readonly=True)

    flags_comment = Text(
        title=u"See `IPOTMsgSet`.flagscomment",
        required=False, readonly=True)

    file_references = Text(
        title=u"See `IPOTMsgSet.filereferences`",
        required=False, readonly=True)

    comment_text = Text(
        title=u"See `ITranslationMessage.commenttext`",
        required=False, readonly=True)

    context = Text(
        title=u"See `IPOTMsgSet`.context",
        required=False, readonly=True)

    msgid_singular = Attribute(_("See `IPOMsgID.pomsgid`"))
    msgid_plural = Attribute(_("See `IPOMsgID.pomsgid`"))


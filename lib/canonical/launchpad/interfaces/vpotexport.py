# Copyright 2006-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces for efficient POT file exports."""

__metaclass__ = type

__all__ = [
    'IVPOTExportSet',
    'IVPOTExport'
    ]

from zope.interface import Interface
from zope.schema import Int, Object, Text

from canonical.launchpad.interfaces import IPOTemplate, IPOTMsgSet


class IVPOTExportSet(Interface):
    """A collection of IVPOTExport-providing rows."""

    def get_potemplate_rows(potemplate):
        """Return all rows which belong to a particular PO template."""


class IVPOTExport(Interface):
    """Database view for efficient POT exports."""

    potemplate = Object(
        title=u"See IPOTemplate",
        required=True, readonly=True, schema=IPOTemplate)

    template_header = Text(
        title=u"See IPOTemplate.header",
        required=True, readonly=True)

    potmsgset = Object(
        title=u"See `IPOTMsgSet`.",
        required=True, readonly=True, schema=IPOTMsgSet)

    sequence = Int(
        title=u"See `IPOTMsgSet`.sequence",
        required=False, readonly=True)

    comment = Text(
        title=u"See `IPOTMsgSet`.commenttext",
        required=False, readonly=True)

    source_comment = Text(
        title=u"See `IPOTMsgSet`.sourcecomment",
        required=False, readonly=True)

    file_references = Text(
        title=u"See `IPOTMsgSet.filereferences`",
        required=False, readonly=True)

    flags_comment = Text(
        title=u"See `IPOTMsgSet`.flagscomment",
        required=False, readonly=True)

    context = Text(
        title=u"See `IPOTMsgSet`.context",
        required=False, readonly=True)

    msgid_singular = Text(
        title=u"See `IPOMsgID`.pomsgid",
        required=True, readonly=True)

    msgid_plural = Text(
        title=u"See `IPOMsgID`.pomsgid",
        required=False, readonly=True)

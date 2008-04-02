# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

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
from canonical.launchpad.interfaces.potmsgset import IPOTMsgSet
from canonical.launchpad.interfaces.translations import TranslationConstants


class IVPOExportSet(Interface):
    """A collection of IVPOExport-providing rows."""

    def get_pofile_rows(pofile):
        """Return exportable rows belonging to the given PO file."""

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


class IVPOExport(Interface):
    """Database view for efficient PO exports."""

    potemplate = Object(
        title=u"Template",
        required=True, readonly=True, schema=IPOTemplate)

    template_header = Text(
        title=u"Template file header",
        description=u"Same as IPOTemplate.header.",
        required=True, readonly=True)

    pofile = Object(
        title=u"Translation file",
        required=True, readonly=True, schema=IPOFile)

    language = Object(
        title=u"Translation language",
        required=True, readonly=True, schema=ILanguage)

    variant = Text(
        title=u"Language variant",
        description=u"As in IPOFile.",
        required=False, readonly=True)

    translation_file_comment = Text(
        title=u"Translation file comment",
        description=u"Same as IPOFile.topcomment.",
        required=False, readonly=True)

    translation_header = Text(
        title=u"Translation file header",
        description=u"Same as IPOFile.header.",
        required=True, readonly=True)

    is_translation_header_fuzzy = Bool(
        title=u"Translation header fuzzy flag",
        description=u"Same as IPOFile.fuzzyheader.",
        required=True, readonly=True)

    potmsgset = Object(
        title=u"See `IPOTMsgSet`.",
        required=True, readonly=True, schema=IPOTMsgSet)

    sequence = Int(
        title=u"Message sequence number",
        description=u"As in IPOTMsgSet.",
        required=True, readonly=True)

    comment = Text(
        title=u"Comment for translated message",
        description=u"Same as IPOTMsgSet.commenttext.",
        required=False, readonly=True)

    source_comment = Text(
        title=u"Comment for original message",
        description=u"Same as IPOTMsgSet.sourcecomment.",
        required=False, readonly=True)

    file_references = Text(
        title=u"Message's source location",
        description=u"Same as IPOTMsgSet.filereferences.",
        required=False, readonly=True)

    flags_comment = Text(
        title=u"Message flags",
        description=u"Same as IPOTMsgSet.flagscomment.",
        required=False, readonly=True)

    context = Text(
        title=u"Message context",
        description=u"As in IPOTMsgSet.", readonly=True, required=False)

    msgid_singular = Text(
        title=u"Message identifier (singular)",
        description=u"See IPOMsgID.pomsgid.",
        required=True, readonly=True)

    msgid_plural = Text(
        title=u"Message identifier (plural)",
        description=u"See IPOMsgID.pomsgid.",
        required=False, readonly=True)

    is_fuzzy = Bool(
        title=u"Message needs review",
        description=u"As in ITranslationMessage.",
        readonly=True, required=False)

    is_current = Bool(
        title=_("Whether this message is currently used in Launchpad"),
        description=u"As in ITranslationMessage.",
        readonly=True, required=True)

    is_imported = Bool(
        title=_("Whether this message was imported"),
        description=u"As in ITranslationMessage.",
        readonly=True, required=True)

    assert TranslationConstants.MAX_PLURAL_FORMS == 6, (
        "Change this code to support %d plural forms."
        % TranslationConstants.MAX_PLURAL_FORMS)

    translation0 = Text(
        title=u"Translation in plural form 0",
        description=u"As in ITranslationMessage.",
        readonly=True, required=False)

    translation1 = Text(
        title=u"Translation in plural form 1",
        description=u"As in ITranslationMessage.",
        readonly=True, required=False)

    translation2 = Text(
        title=u"Translation in plural form 2",
        description=u"As in ITranslationMessage.",
        readonly=True, required=False)

    translation3 = Text(
        title=u"Translation in plural form 3",
        description=u"As in ITranslationMessage.",
        readonly=True, required=False)

    translation4 = Text(
        title=u"Translation in plural form 4",
        description=u"As in ITranslationMessage.",
        readonly=True, required=False)

    translation5 = Text(
        title=u"Translation in plural form 5",
        description=u"As in ITranslationMessage.",
        readonly=True, required=False)


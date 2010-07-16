# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

from zope.interface import Attribute, Interface
from zope.schema import (
    Choice, Datetime, Object)

from lazr.enum import DBEnumeratedType, DBItem

from canonical.launchpad import _
from lp.translations.interfaces.potemplate import IHasTranslationTemplates
from lp.registry.interfaces.person import IPerson

__metaclass__ = type

__all__ = (
    'ITranslatedLanguage',
    'TranslationConstants',
    'TranslationsBranchImportMode',
    )

class TranslationConstants:
    """Set of constants used inside the context of translations."""

    SINGULAR_FORM = 0
    PLURAL_FORM = 1

    # Largest number of plural forms any language can have.
    MAX_PLURAL_FORMS = 6

    SPACE_CHAR = '<samp> </samp>'
    NEWLINE_CHAR = '<img alt="" src="/@@/translation-newline" /><br/>\n'
    TAB_CHAR = '<code>[tab]</code>'
    TAB_CHAR_ESCAPED = '<code>' + r'\[tab]' + '</code>'
    NO_BREAK_SPACE_CHAR = '<code>[nbsp]</code>'
    NO_BREAK_SPACE_CHAR_ESCAPED = '<code>' + r'\[nbsp]' + '</code>'


class TranslationsBranchImportMode(DBEnumeratedType):
    """How translations from a Bazaar branch should be synchronized."""

    NO_IMPORT = DBItem(1, """
        None

        Do not import any templates or translations from the branch.
        """)

    IMPORT_TEMPLATES = DBItem(2, """
        Import template files

        Import all translation template files found in the branch.
        """)

    IMPORT_TRANSLATIONS = DBItem(3, """
        Import template and translation files

        Import all translation files (templates and translations)
        found in the branch.
        """)


class ITranslatedLanguage(Interface):
    """Interface for providing translations for context by language.

    It expects `parent` to provide `IHasTranslationTemplates`."""

    language = Choice(
        title=_('Language to gather statistics and POFiles for.'),
        vocabulary='Language', required=True)

    parent = Object(
        title=_('A parent with translation templates.'),
        schema=IHasTranslationTemplates)

    pofiles = Attribute(
        'Iterator over all POFiles for this context and language.')

    translation_statistics = Attribute(
        _('A dict containing relevant aggregated statistics counts.'))

    def setCounts(total, imported, changed, new, unreviewed, last_changed):
        """Set aggregated message counts for ITranslatedLanguage."""

    def recalculateCounts():
        """Recalculate message counts for this ITranslatedLanguage."""

    last_changed_date = Datetime(
        title=_('When was this translation last changed.'),
        readonly=False, required=True)

    last_translator = Object(
        title=_('Last person that translated something in this context.'),
        schema=IPerson)

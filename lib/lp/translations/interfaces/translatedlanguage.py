# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

from zope.interface import Attribute, Interface
from zope.schema import (
    Choice, Datetime, Object)

from canonical.launchpad import _
from lp.services.worlddata.interfaces.language import ILanguage
from lp.translations.interfaces.potemplate import IHasTranslationTemplates
from lp.registry.interfaces.person import IPerson

__metaclass__ = type

__all__ = [
    'ITranslatedLanguage',
    ]

class ITranslatedLanguage(Interface):
    """Interface for providing translations for context by language.

    It expects `parent` to provide `IHasTranslationTemplates`."""

    language = Object(
        title=_('Language to gather statistics and POFiles for.'),
        schema=ILanguage)

    parent = Object(
        title=_('A parent with translation templates.'),
        schema=IHasTranslationTemplates)

    pofiles = Attribute(
        _('Iterator over all POFiles for this context and language.'))

    translation_statistics = Attribute(
        _('A dict containing relevant aggregated statistics counts.'))

    def setCounts(total, translated, new, changed, unreviewed):
        """Set aggregated message counts for ITranslatedLanguage."""

    def recalculateCounts():
        """Recalculate message counts for this ITranslatedLanguage."""

    last_changed_date = Datetime(
        title=_('When was this translation last changed.'),
        readonly=False, required=True)

    last_translator = Object(
        title=_('Last person that translated something in this context.'),
        schema=IPerson)

# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = ['TranslatedLanguageMixin']

from zope.interface import implements

from storm.expr import Coalesce, Desc, Sum

from lp.translations.interfaces.potemplate import IHasTranslationTemplates
from lp.translations.interfaces.translations import ITranslatedLanguage
from lp.translations.model.pofile import POFile
from lp.translations.model.potemplate import POTemplate

class TranslatedLanguageMixin(object):
    """See `ITranslatedLanguage`."""
    implements(ITranslatedLanguage)

    language = None
    parent = None

    def __init__(self):
        self.setCounts(total=0, translated=0, new=0, changed=0, unreviewed=0)

    @property
    def pofiles(self):
        """See `ITranslatedLanguage`."""
        assert IHasTranslationTemplates.providedBy(self.parent), (
            "Parent object should implement `IHasTranslationTemplates`.")
        current_templates = self.parent.getCurrentTemplatesCollection()
        pofiles = current_templates.joinPOFile()
        return pofiles.select(POFile).order_by(
            Desc(POTemplate.priority), POTemplate.name)

    @property
    def translation_statistics(self):
        return self._translation_statistics

    def setCounts(self, total, translated, new, changed, unreviewed):
        """See `ITranslatedLanguage`."""
        untranslated = total - translated
        self._translation_statistics = {
            'total_count' : total,
            'translated_count' : translated,
            'new_count' : new,
            'changed_count' : changed,
            'unreviewed_count' : unreviewed,
            'untranslated_count' : untranslated,
            }

    def recalculateCounts(self):
        """See `ITranslatedLanguage`."""
        templates = self.parent.getCurrentTemplatesCollection()
        pofiles = templates.joinPOFile()
        total_count_results = list(
            pofiles.select(Coalesce(Sum(POTemplate.messagecount), 0),
                           Coalesce(Sum(POFile.currentcount), 0),
                           Coalesce(Sum(POFile.updatescount), 0),
                           Coalesce(Sum(POFile.rosettacount), 0),
                           Coalesce(Sum(POFile.unreviewed_count), 0))
            )
        total, imported, changed, rosetta, unreviewed = total_count_results[0]
        translated = imported + rosetta
        new = rosetta - changed
        self.setCounts(total, translated, new, changed, unreviewed)

    last_changed_date = None
    last_translator = None

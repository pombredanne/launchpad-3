# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = ['TranslatedLanguageMixin']

from zope.interface import implements

from storm.expr import Desc

from lp.translations.interfaces.potemplate import IHasTranslationTemplates
from lp.translations.interfaces.translations import ITranslatedLanguage
from lp.translations.model.pofile import POFile
from lp.translations.model.potemplate import POTemplate

class TranslatedLanguageMixin(object):
    """See `ITranslatedLanguage`."""
    implements(ITranslatedLanguage)

    language = None
    parent = None

    @property
    def pofiles(self):
        """See `ITranslatedLanguage`."""
        assert IHasTranslationTemplates.providedBy(self.parent), (
            "Parent object should implement `IHasTranslationTemplates`.")
        current_templates = self.parent.getCurrentTemplatesCollection()
        pofiles = current_templates.joinPOFile()
        return pofiles.select(POFile).order_by(
            Desc(POTemplate.priority), POTemplate.name)

    translation_statistics = None

    def setCounts(self, total, imported, changed, new,
                  unreviewed, last_changed):
        """See `ITranslatedLanguage`."""
        pass

    def recalculateCounts(self):
        """See `ITranslatedLanguage`."""
        pass

    last_changed_date = None
    last_translator = None

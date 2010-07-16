# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = ['TranslatedLanguageMixin']

from zope.interface import implements

from lp.translations.interfaces.translations import ITranslatedLanguage

class TranslatedLanguageMixin(object):
    """See `ITranslatedLanguage`."""
    implements(ITranslatedLanguage)

    language = None
    parent = None

    pofiles = None
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

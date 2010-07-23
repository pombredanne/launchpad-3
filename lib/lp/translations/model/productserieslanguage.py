# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation for `IProductSeriesLanguage`."""

__metaclass__ = type

__all__ = [
    'ProductSeriesLanguage',
    'ProductSeriesLanguageSet',
    ]

from zope.interface import implements

from lp.translations.utilities.rosettastats import RosettaStats
from lp.translations.model.potemplate import get_pofiles_for
from lp.translations.model.translatedlanguage import TranslatedLanguageMixin
from lp.translations.interfaces.productserieslanguage import (
    IProductSeriesLanguage, IProductSeriesLanguageSet)


class ProductSeriesLanguage(RosettaStats, TranslatedLanguageMixin):
    """See `IProductSeriesLanguage`."""
    implements(IProductSeriesLanguage)

    def __init__(self, productseries, language, variant=None, pofile=None):
        assert 'en' != language.code, (
            'English is not a translatable language.')
        RosettaStats.__init__(self)
        TranslatedLanguageMixin.__init__(self)
        self.productseries = productseries
        self.parent = productseries
        self.language = language
        self.variant = variant
        self.pofile = pofile
        self.id = 0
        self.last_changed_date = None

    @property
    def title(self):
        """See `IProductSeriesLanguage`."""
        return '%s translations for %s %s' % (
            self.language.englishname,
            self.productseries.product.displayname,
            self.productseries.displayname)

    def messageCount(self):
        """See `IRosettaStats`."""
        return self._translation_statistics['total_count']

    def currentCount(self, language=None):
        """See `IRosettaStats`."""
        translated = self._translation_statistics['translated_count']
        new = self._translation_statistics['new_count']
        changed = self._translation_statistics['changed_count']
        current = translated - new - changed
        return current

    def updatesCount(self, language=None):
        """See `IRosettaStats`."""
        return self._translation_statistics['changed_count']

    def rosettaCount(self, language=None):
        """See `IRosettaStats`."""
        new = self._translation_statistics['new_count']
        changed = self._translation_statistics['changed_count']
        rosetta = new + changed
        return rosetta

    def unreviewedCount(self):
        """See `IRosettaStats`."""
        return self._translation_statistics['unreviewed_count']


class ProductSeriesLanguageSet:
    """See `IProductSeriesLanguageSet`.

    Provides a means to get a ProductSeriesLanguage.
    """
    implements(IProductSeriesLanguageSet)

    def getProductSeriesLanguage(self, productseries, language,
                                 variant=None, pofile=None):
        """See `IProductSeriesLanguageSet`."""
        return ProductSeriesLanguage(productseries, language, variant, pofile)

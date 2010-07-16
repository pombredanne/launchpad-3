# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation for `IProductSeriesLanguage`."""

__metaclass__ = type

__all__ = [
    'DummyProductSeriesLanguage',
    'ProductSeriesLanguage',
    'ProductSeriesLanguageSet',
    ]

from zope.interface import implements

from storm.expr import Sum
from storm.store import Store

from lp.translations.utilities.rosettastats import RosettaStats
from lp.translations.model.pofile import DummyPOFile, POFile
from lp.translations.model.potemplate import get_pofiles_for, POTemplate
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
        self._last_changed_date = None

    def _setCounts(self, total=None, imported=None, changed=None, new=None,
                  unreviewed=None, last_changed=None):
        """See `IProductSeriesLanguage`."""
        self._messagecount = total
        # "currentcount" in RosettaStats conflicts our recent terminology
        # and is closer to "imported" (except that it doesn't include
        # "changed") translations.
        self._currentcount = imported
        self._updatescount = changed
        self._rosettacount = new
        self._unreviewed_count = unreviewed
        if last_changed is not None:
            self._last_changed_date = last_changed


    def _getMessageCount(self):
        store = Store.of(self.language)
        query = store.find(Sum(POTemplate.messagecount),
                           POTemplate.productseries==self.productseries,
                           POTemplate.iscurrent==True)
        total, = query
        if total is None:
            total = 0
        return total

    @property
    def title(self):
        """See `IProductSeriesLanguage`."""
        return '%s translations for %s %s' % (
            self.language.englishname,
            self.productseries.product.displayname,
            self.productseries.displayname)

    def messageCount(self):
        """See `IProductSeriesLanguage`."""
        return self._messagecount

    def currentCount(self, language=None):
        """See `IProductSeriesLanguage`."""
        return self._currentcount

    def updatesCount(self, language=None):
        """See `IProductSeriesLanguage`."""
        return self._updatescount

    def rosettaCount(self, language=None):
        """See `IProductSeriesLanguage`."""
        return self._rosettacount

    def unreviewedCount(self):
        """See `IProductSeriesLanguage`."""
        return self._unreviewed_count

    @property
    def last_changed_date(self):
        """See `IProductSeriesLanguage`."""
        return self._last_changed_date

    def getPOFilesFor(self, potemplates):
        """See `IProductSeriesLanguage`."""
        return get_pofiles_for(potemplates, self.language, self.variant)


class DummyProductSeriesLanguage(ProductSeriesLanguage):
    """See `IProductSeriesLanguage`.

    Implementation of IProductSeriesLanguage for a language with no
    translations.
    """
    implements(IProductSeriesLanguage)

    def __init__(self, productseries, language, variant=None, pofile=None):
        ProductSeriesLanguage.__init__(
            self, productseries, language, variant, pofile)
        self.setCounts(self._getMessageCount(), 0, 0, 0, 0)

    def getPOFilesFor(self, potemplates):
        """See `IProductSeriesLanguage`."""
        return [
            DummyPOFile(template, self.language, self.variant)
            for template in potemplates
            ]


class ProductSeriesLanguageSet:
    """See `IProductSeriesLanguageSet`.

    Provides a means to get a ProductSeriesLanguage or create a dummy.
    """
    implements(IProductSeriesLanguageSet)

    def getProductSeriesLanguage(self, productseries, language,
                                 variant=None):
        """See `IProductSeriesLanguageSet`."""
        return ProductSeriesLanguage(productseries, language, variant)

    def getDummy(self, productseries, language, variant=None, pofile=None):
        """See `IProductSeriesLanguageSet`."""
        return DummyProductSeriesLanguage(
            productseries, language, variant, pofile)

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation for `IProductSeriesLanguage`."""

__metaclass__ = type

__all__ = [
    'ProductSeriesLanguage',
    'ProductSeriesLanguageSet',
    ]

from zope.interface import implements

from storm.expr import Sum
from storm.store import Store

from lp.translations.utilities.rosettastats import RosettaStats
from lp.translations.model.pofile import DummyPOFile, POFile
from lp.translations.model.potemplate import get_pofiles_for, POTemplate
from lp.translations.interfaces.productserieslanguage import (
    IProductSeriesLanguage, IProductSeriesLanguageSet)


class ProductSeriesLanguage(RosettaStats):
    """See `IProductSeriesLanguage`."""
    implements(IProductSeriesLanguage)

    def __init__(self, productseries, language, variant=None, pofile=None):
        assert 'en' != language.code, (
            'English is not a translatable language.')
        RosettaStats.__init__(self)
        self.productseries = productseries
        self.language = language
        self.variant = variant
        self.pofile = pofile
        self.id = 0
        self._last_changed_date = None

        # Reset all cached counts.
        self.setCounts()

    def setCounts(self, total=None, imported=None, changed=None, new=None,
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

    def recalculateCounts(self):
        """See `IProductSeriesLanguage`."""
        store = Store.of(self.language)
        query = store.find(
            (Sum(POFile.currentcount),
              Sum(POFile.updatescount),
              Sum(POFile.rosettacount),
              Sum(POFile.unreviewed_count)),
            POFile.language==self.language,
            POFile.variant==None,
            POFile.potemplate==POTemplate.id,
            POTemplate.productseries==self.productseries,
            POTemplate.iscurrent==True)
        imported, changed, new, unreviewed = query[0]
        if (imported is None or changed is None or
            new is None or unreviewed is None):
            # Set all counts to zero.
            imported = changed = new = unreviewed = 0
        self.setCounts(self._getMessageCount(), imported, changed,
                       new, unreviewed)

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

    @property
    def pofiles(self):
        """See `IProductSeriesLanguage`."""
        store = Store.of(self.language)
        result = store.find(
            POFile,
            POFile.language==self.language,
            POFile.variant==self.variant,
            POFile.potemplate==POTemplate.id,
            POTemplate.productseries==self.productseries,
            POTemplate.iscurrent==True)
        return result.order_by(['-priority'])

    def getPOFilesFor(self, potemplates):
        """See `IProductSeriesLanguage`."""
        return get_pofiles_for(potemplates, self.language, self.variant)


class ProductSeriesLanguageSet:
    """See `IProductSeriesLanguageSet`.

    Provides a means to get a ProductSeriesLanguage or create a dummy.
    """
    implements(IProductSeriesLanguageSet)

    def getProductSeriesLanguage(self, productseries, language,
                                 variant=None, pofile=None):
        """See `IProductSeriesLanguageSet`."""
        return ProductSeriesLanguage(productseries, language, variant, pofile)

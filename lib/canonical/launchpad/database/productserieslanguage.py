# Copyright 2009 Canonical Ltd.  All rights reserved.

"""An implementation of ProductSeriesLanguage objects."""

__metaclass__ = type

__all__ = [
    'DummyProductSeriesLanguage',
    'ProductSeriesLanguage',
    'ProductSeriesLanguageSet',
    ]

from zope.interface import implements

from storm.expr import Sum
from storm.store import Store

from canonical.launchpad.components.rosettastats import RosettaStats
from canonical.launchpad.database.pofile import POFile
from canonical.launchpad.database.potemplate import POTemplate
from canonical.launchpad.interfaces import (
    IProductSeriesLanguage, IProductSeriesLanguageSet)

class ProductSeriesLanguage(RosettaStats):
    """See `IProductSeriesLanguage`.

    Implementation of IProductSeriesLanguage.
    """
    implements(IProductSeriesLanguage)

    def __init__(self, productseries, language, variant=None, pofile=None):
        assert 'en' != language.code, (
            'English is not a translatable language.')
        RosettaStats.__init__(self)
        self.productseries = productseries
        self._language = language
        self.pofile = pofile
        self.variant = variant
        self.id = 0

        # Reset all cached counts.
        self.setCounts()

    def setCounts(self, total=None, imported=None, changed=None, new=None,
                  unreviewed=None):
        self._messagecount = total
        self._currentcount = imported
        self._updatescount = changed
        self._rosettacount = new
        self._unreviewed_count = unreviewed

    @property
    def language(self):
        return self._language

    def testStatistics(self):
        """See `IProductSeriesLanguage`."""
        pass

    @property
    def title(self):
        """See `IProductSeriesLanguage`."""
        return self.language.englishname

    def updateStatistics(self):
        """See `IProductSeriesLanguage`."""
        pass

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

    @property
    def pofiles_or_dummies(self):
        """See `IProductSeriesLanguage`."""
        store = Store.of(self.language)

        all_templates = store.find(
            POTemplate,
            POTemplate.productseries==self.productseries,
            POTemplate.iscurrent==True)

        existing_pofiles = {}
        for pofile in self.pofiles:
            existing_pofiles[pofile.potemplate] = pofile

        all_pofiles = []
        for potemplate in all_templates.order_by(['-priority']):
            if existing_pofiles.has_key(potemplate):
                pofile = existing_pofiles[potemplate]
            else:
                pofile = potemplate.getDummyPOFile(
                    self.language.code, self.variant)
            all_pofiles.append(pofile)

        return all_pofiles


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

    def _getMessageCount(self):
        store = Store.of(self.language)
        query = store.find(Sum(POTemplate.messagecount),
                           POTemplate.productseries==self.productseries,
                           POTemplate.iscurrent==True)
        total, = query
        if total is None:
            total = 0
        return total


class ProductSeriesLanguageSet:
    """See `IProductSeriesLanguageSet`.

    Implements a means to get a DummyProductSeriesLanguage.
    """
    implements(IProductSeriesLanguageSet)

    def getForProductSeriesAndLanguage(self, productseries, language,
                                       variant=None):
        """See `IProductSeriesLanguageSet`."""
        return ProductSeriesLanguage(productseries, language, variant)

    def getDummy(self, productseries, language, variant=None, pofile=None):
        """See `IProductSeriesLanguageSet`."""
        return DummyProductSeriesLanguage(
            productseries, language, variant, pofile)

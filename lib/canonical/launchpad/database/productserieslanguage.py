# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""An implementation of ProductSeriesLanguage objects."""

__metaclass__ = type

__all__ = [
    'DummyProductSeriesLanguage',
    'ProductSeriesLanguage',
    'ProductSeriesLanguageSet',
    ]

from zope.interface import implements

from storm.store import Store

from canonical.launchpad.components.rosettastats import RosettaStats
from canonical.launchpad.database.pofile import POFile
from canonical.launchpad.database.potemplate import POTemplate
from canonical.launchpad.interfaces import (
    IProductSeriesLanguage, IProductSeriesLanguageSet)

from canonical.database.sqlbase import (
    cursor, sqlvalues)

class ProductSeriesLanguage(RosettaStats):
    """See `IProductSeriesLanguage`.

    Implementation of IProductSeriesLanguage.
    """
    implements(IProductSeriesLanguage)

    def __init__(self, productseries, language, variant=None, pofile=None):
        assert 'en' != language.code, (
            'English is not a translatable language.')
        self.productseries = productseries
        self._language = language
        self.pofile = pofile
        self.variant = variant
        self.id = 0
        self._getMessageCount()
        self._getTranslationCounts()

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

    def _getMessageCount(self):
        query = """
        SELECT SUM(messagecount)
          FROM POTemplate
          WHERE productseries=%s""" % sqlvalues(self.productseries)
        cur = cursor()
        cur.execute(query)
        self._messagecount = cur.fetchall()[0][0]

    def _getTranslationCounts(self):
        # Sets all POFile SUM counts.
        if self.variant is None:
            variant_query = "POFile.variant IS NULL"
        else:
            variant_query = "POFile.variant = %s" % sqlvalues(self.variant)
        sum_stats_query = """
          SELECT SUM(currentcount), SUM(updatescount),
                 SUM(rosettacount), SUM(unreviewed_count)
            FROM POFile
            JOIN POTemplate ON
              POTemplate.id = POFile.potemplate
            WHERE
              POFile.language = %s AND """
        sum_stats_query += variant_query + " AND "
        sum_stats_query += "POTemplate.productseries = %s"
        query = sum_stats_query % sqlvalues(self.language,
                                            self.productseries)
        cur = cursor()
        cur.execute(query)
        (self._currentcount, self._updatescount, self._rosettacount,
         self._unreviewed_count) = cur.fetchall()[0]

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
        assert 'en' != language.code, (
            'English is not a translatable language.')
        self.productseries = productseries
        self._language = language
        self.pofile = pofile
        self.variant = variant
        self.id = 0
        self._getMessageCount()

    def testStatistics(self):
        """See `IProductSeriesLanguage`."""
        pass

    def updateStatistics(self):
        """See `IProductSeriesLanguage`."""
        pass

    def _getMessageCount(self):
        query = """
        SELECT SUM(messagecount)
          FROM POTemplate
          WHERE productseries=%s""" % sqlvalues(self.productseries)
        cur = cursor()
        cur.execute(query)
        self._messagecount = cur.fetchall()[0][0]
        if self._messagecount is None:
            self._messagecount = 0

    def messageCount(self):
        """See `IProductSeriesLanguage`."""
        return self._messagecount

    def currentCount(self, language=None):
        """See `IProductSeriesLanguage`."""
        return 0

    def updatesCount(self, language=None):
        """See `IProductSeriesLanguage`."""
        return 0

    def rosettaCount(self, language=None):
        """See `IProductSeriesLanguage`."""
        return 0

    def unreviewedCount(self):
        """See `IProductSeriesLanguage`."""
        return 0


class ProductSeriesLanguageSet:
    """See `IProductSeriesLanguageSet`.

    Implements a means to get a DummyProductSeriesLanguage.
    """
    implements(IProductSeriesLanguageSet)

    def getForProductSeriesAndLanguage(self, productseries, language,
                                       variant=None):
        """See `IProductSeriesLanguageSet`."""
        # XXX (FIXME): return dummy if it doesn't exist for speed reasons.
        return ProductSeriesLanguage(productseries, language, variant)

    def getDummy(self, productseries, language, variant=None, pofile=None):
        """See `IProductSeriesLanguageSet`."""
        return DummyProductSeriesLanguage(
            productseries, language, variant, pofile)

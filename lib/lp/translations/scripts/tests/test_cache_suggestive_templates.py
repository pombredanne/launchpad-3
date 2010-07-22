# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test script that refreshes the suggestive-POTemplates cache."""

__metaclass__ = type

import transaction
import unittest

from zope.component import getUtility

from canonical.launchpad.ftests.script import run_script
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, DEFAULT_FLAVOR, MAIN_STORE)
from canonical.testing.layers import ZopelessDatabaseLayer
from lp.testing import TestCase, TestCaseWithFactory

from lp.translations.interfaces.potemplate import IPOTemplateSet
from lp.translations.scripts.cachesuggestivepotemplates import (
    CacheSuggestivePOTemplates)


class TestSuggestivePOTemplatesCache(TestCaseWithFactory):
    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestSuggestivePOTemplatesCache, self).setUp()
        self.utility = getUtility(IPOTemplateSet)

    def _refreshCache(self):
        """Refresh the cache, but do not commit."""
        self.utility.wipeSuggestivePOTemplatesCache()
        self.utility.populateSuggestivePOTemplatesCache()

    def _readCache(self):
        """Read cache contents, in deterministic order."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        result = store.execute(
            "SELECT * FROM SuggestivePOTemplate ORDER BY potemplate")
        return [id for id, in result.get_all()]

    def test_consistent_contents(self):
        # Refreshing the cache will reproduce the same cache if there
        # have been no intervening template changes.
        self._refreshCache()
        contents = self._readCache()
        self._refreshCache()
        self.assertEqual(contents, self._readCache())

    def test_wipe(self):
        # The wipe method clears the cache.
        self._refreshCache()
        self.assertNotEqual([], self._readCache())

        self.utility.wipeSuggestivePOTemplatesCache()

        self.assertEqual([], self._readCache())

    def test_populate(self):
        # The populate method fills an empty cache.
        self.utility.wipeSuggestivePOTemplatesCache()
        self.utility.populateSuggestivePOTemplatesCache()
        self.assertNotEqual([], self._readCache())

    def test_main(self):
        # The main method repopulates the cache, and commits.
        self._refreshCache()
        cache_before = self._readCache()

        pot = self.factory.makePOTemplate()
        CacheSuggestivePOTemplates(test_args=['-q']).main()

        # main() committed, so aborting here has no effect.
        transaction.abort()

        cache_after = self._readCache()
        self.assertNotEqual(cache_before, cache_after)
        self.assertContentEqual(cache_before + [pot.id], cache_after)

    def test_new_template(self):
        # A new template appears in the cache on the next refresh.
        self._refreshCache()
        cache_before = self._readCache()

        pot = self.factory.makePOTemplate()
        self._refreshCache()

        self.assertContentEqual(cache_before + [pot.id], self._readCache())

    def test_product_official_rosetta(self):
        # Templates from projects are included in the cache only where
        # the project uses Launchpad Translations.
        productseries = self.factory.makeProductSeries()
        productseries.product.official_rosetta = True
        pot = self.factory.makePOTemplate(productseries=productseries)
        self._refreshCache()

        cache_with_template = self._readCache()

        productseries.product.official_rosetta = False
        self._refreshCache()

        cache_without_template = self._readCache()
        self.assertNotEqual(cache_with_template, cache_without_template)
        self.assertContentEqual(
            cache_with_template, cache_without_template + [pot.id])

    def test_distro_official_rosetta(self):
        # Templates from distributions are included in the cache only
        # where the distribution uses Launchpad Translations.
        package = self.factory.makeSourcePackage()
        package.distroseries.distribution.official_rosetta = True
        pot = self.factory.makePOTemplate(
            distroseries=package.distroseries,
            sourcepackagename=package.sourcepackagename)
        self._refreshCache()

        cache_with_template = self._readCache()

        package.distroseries.distribution.official_rosetta = False
        self._refreshCache()

        cache_without_template = self._readCache()
        self.assertNotEqual(cache_with_template, cache_without_template)
        self.assertContentEqual(
            cache_with_template, cache_without_template + [pot.id])

    def test_disabled_template(self):
        # A template that is not current is excluded from the cache.
        self._refreshCache()
        cache_before = self._readCache()

        pot = self.factory.makePOTemplate()
        pot.iscurrent = False
        self._refreshCache()

        self.assertEqual(cache_before, self._readCache())

    def test_dry_run(self):
        # The --dry-run option inhibits any real database changes.
        self._refreshCache()
        cache_before = self._readCache()

        potemplate = self.factory.makePOTemplate()
        CacheSuggestivePOTemplates(test_args=['--dry-run', '-q']).main()

        self.assertEqual(cache_before, self._readCache())


class TestCacheSuggestivePOTemplatesScript(TestCase):
    """Test real script run.  Costly, so do only once."""

    def test_run_script(self):
        (returncode, stdout, stderr) = run_script(
            'cronscripts/cache-suggestive-potemplates.py', ['--dry-run'])
        self.assertEqual(0, returncode)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

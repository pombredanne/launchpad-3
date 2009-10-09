# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import logging
import re

from unittest import TestLoader

from lp.testing import TestCaseWithFactory
from canonical.testing.layers import LaunchpadScriptLayer

from lp.translations.model.translationimportqueue import (
    TranslationImportQueue)
from lp.translations.scripts.po_import import TranslationsImport


class TestTranslationsImport(TestCaseWithFactory):

    layer = LaunchpadScriptLayer

    def setUp(self):
        super(TestTranslationsImport, self).setUp()
        self.queue = TranslationImportQueue()
        self.script = TranslationsImport('poimport', test_args=[])
        self.script.logger.setLevel(logging.FATAL)
        self.owner = self.factory.makePerson()

    def _makeProductSeries(self):
        """Make a product series called 'trunk'."""
        return self.factory.makeProduct(owner=self.owner).getSeries('trunk')

    def _makeEntry(self, path, **kwargs):
        """Produce a queue entry."""
        return self.queue.addOrUpdateEntry(
            path, '# Nothing here', False, self.owner, **kwargs)

    def test_describeEntry_without_target(self):
        productseries = self._makeProductSeries()
        entry = self._makeEntry('foo.po', productseries=productseries)
        description = self.script._describeEntry(entry)
        pattern = "'foo.po' \(id [0-9]+\) in [A-Za-z0-9_-]+ trunk series$"
        self.assertNotEqual(None, re.match(pattern, description))

    def test_describeEntry_for_pofile(self):
        productseries = self._makeProductSeries()
        template = self.factory.makePOTemplate(productseries=productseries)
        pofile = template.newPOFile('nl')
        entry = self._makeEntry(
            'foo.po', productseries=productseries, potemplate=template,
            pofile=pofile)
        description = self.script._describeEntry(entry)
        pattern = "Dutch \(nl\) translation of .* in .* trunk \(id [0-9]+\)$"
        self.assertNotEqual(None, re.match(pattern, description))

    def test_describeEntry_for_template(self):
        productseries = self._makeProductSeries()
        template = self.factory.makePOTemplate(productseries=productseries)
        entry = self._makeEntry(
            'foo.pot', productseries=productseries, potemplate=template)
        description = self.script._describeEntry(entry)
        pattern = 'Template "[^"]+" in [A-Za-z0-9_-]+ trunk \(id [0-9]+\)$'
        self.assertNotEqual(None, re.match(pattern, description))

    def test_checkEntry(self):
        productseries = self._makeProductSeries()
        template = self.factory.makePOTemplate(productseries=productseries)
        entry = self._makeEntry(
            'foo.pot', productseries=productseries, potemplate=template)
        self.assertTrue(self.script._checkEntry(entry))

    def test_checkEntry_without_target(self):
        productseries = self._makeProductSeries()
        entry = self._makeEntry('foo.pot', productseries=productseries)
        self.assertFalse(self.script._checkEntry(entry))
        self.assertIn(
            "Entry is approved but has no place to import to.",
            self.script.failures.keys())

    def test_checkEntry_misapproved_product(self):
        productseries = self._makeProductSeries()
        template = self.factory.makePOTemplate()
        entry = self._makeEntry(
            'foo.pot', productseries=productseries, potemplate=template)
        self.assertNotEqual(None, entry.import_into)

        self.assertFalse(self.script._checkEntry(entry))
        self.assertIn(
            "Entry was approved for the wrong productseries.",
            self.script.failures.keys())

    def test_checkEntry_misapproved_package(self):
        package = self.factory.makeSourcePackage()
        other_series = self.factory.makeDistroRelease(
            distribution=package.distroseries.distribution)
        template = self.factory.makePOTemplate(
            distroseries=package.distroseries,
            sourcepackagename=package.sourcepackagename)
        entry = self._makeEntry(
            'foo.pot', sourcepackagename=package.sourcepackagename,
            distroseries=other_series, potemplate=template)
        self.assertNotEqual(None, entry.import_into)

        self.assertFalse(self.script._checkEntry(entry))
        self.assertIn(
            "Entry was approved for the wrong distroseries.",
            self.script.failures.keys())


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

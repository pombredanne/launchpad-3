# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import ZopelessDatabaseLayer
from lp.testing import TestCaseWithFactory
from lp.translations.interfaces.side import (
    TranslationSide,
    )
from lp.translations.utilities.translationsplitter import (
    TranslationSplitter,
    )


class TestTranslationSplitter(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def useInTemplate(self, potmsgset, potemplate):
        return potmsgset.setSequence(
            potemplate, self.factory.getUniqueInteger())

    def test_findShared_requires_both(self):
        """Results are only included when both sides have the POTMsgSet."""
        upstream_template = self.factory.makePOTemplate(
            side=TranslationSide.UPSTREAM)
        productseries = upstream_template.productseries
        ubuntu_template = self.factory.makePOTemplate(
            side=TranslationSide.UBUNTU)
        package = ubuntu_template.sourcepackage
        potmsgset = self.factory.makePOTMsgSet(upstream_template, sequence=1)
        splitter = TranslationSplitter(productseries, package)
        self.assertContentEqual([], splitter.findShared())
        (upstream_item,) = potmsgset.getAllTranslationTemplateItems()
        ubuntu_item = self.useInTemplate(potmsgset, ubuntu_template)
        self.assertContentEqual(
            [(upstream_item, ubuntu_item)], splitter.findShared())
        removeSecurityProxy(upstream_item).destroySelf()
        self.assertContentEqual([], splitter.findShared())

    def makeTranslationSplitter(self):
        return TranslationSplitter(
            self.factory.makeProductSeries(),
            self.factory.makeSourcePackage())

    def makeSharedPOTMsgSet(self, splitter):
        upstream_template = self.factory.makePOTemplate(
            productseries=splitter.productseries)
        potmsgset = self.factory.makePOTMsgSet(
            upstream_template, sequence=self.factory.getUniqueInteger())
        (upstream_item,) = potmsgset.getAllTranslationTemplateItems()
        ubuntu_template = self.factory.makePOTemplate(
            sourcepackage=splitter.sourcepackage)
        ubuntu_item = self.useInTemplate(potmsgset, ubuntu_template)
        return upstream_item, ubuntu_item

    def test_findSharedGroupsPOTMsgSet(self):
        """POTMsgSets are correctly grouped."""
        splitter = self.makeTranslationSplitter()
        self.makeSharedPOTMsgSet(splitter)
        self.makeSharedPOTMsgSet(splitter)
        for num, (upstream, ubuntu) in enumerate(splitter.findShared()):
            self.assertEqual(upstream.potmsgset, ubuntu.potmsgset)
        self.assertEqual(1, num)

    def test_splitPOTMsgSet(self):
        """Splitting a POTMsgSet clones it and updates TemplateItem."""
        splitter = self.makeTranslationSplitter()
        upstream_item, ubuntu_item = self.makeSharedPOTMsgSet(splitter)
        ubuntu_template = ubuntu_item.potemplate
        ubuntu_sequence = ubuntu_item.sequence
        new_potmsgset = splitter.splitPOTMsgSet(ubuntu_item)
        self.assertEqual(new_potmsgset, ubuntu_item.potmsgset)

    def test_migrateTranslations_diverged_upstream(self):
        """Diverged upstream translation stays put."""
        splitter = self.makeTranslationSplitter()
        upstream_item, ubuntu_item = self.makeSharedPOTMsgSet(splitter)
        upstream_message = self.factory.makeCurrentTranslationMessage(
            potmsgset=upstream_item.potmsgset,
            potemplate=upstream_item.potemplate, diverged=True)
        splitter.splitPOTMsgSet(ubuntu_item)
        upstream_translation = splitter.migrateTranslations(
            upstream_item.potmsgset, ubuntu_item)
        self.assertEqual(
            upstream_message,
            upstream_item.potmsgset.getAllTranslationMessages().one())
        self.assertIs(
            None, ubuntu_item.potmsgset.getAllTranslationMessages().one())

    def test_migrateTranslations_diverged_ubuntu(self):
        """Diverged ubuntu translation moves."""
        splitter = self.makeTranslationSplitter()
        upstream_item, ubuntu_item = self.makeSharedPOTMsgSet(splitter)
        ubuntu_message = self.factory.makeCurrentTranslationMessage(
            potmsgset=ubuntu_item.potmsgset,
            potemplate=ubuntu_item.potemplate, diverged=True)
        splitter.splitPOTMsgSet(ubuntu_item)
        upstream_translation = splitter.migrateTranslations(
            upstream_item.potmsgset, ubuntu_item)
        self.assertEqual(
            ubuntu_message,
            ubuntu_item.potmsgset.getAllTranslationMessages().one())
        self.assertIs(
            None,
            upstream_item.potmsgset.getAllTranslationMessages().one())

    def test_migrateTranslations_shared(self):
        """Shared translation is copied."""
        splitter = self.makeTranslationSplitter()
        upstream_item, ubuntu_item = self.makeSharedPOTMsgSet(splitter)
        self.factory.makeCurrentTranslationMessage(
            potmsgset=upstream_item.potmsgset)
        splitter.splitPOTMsgSet(ubuntu_item)
        splitter.migrateTranslations(upstream_item.potmsgset, ubuntu_item)
        (upstream_translation,) = (
            upstream_item.potmsgset.getAllTranslationMessages())
        (ubuntu_translation,) = (
            ubuntu_item.potmsgset.getAllTranslationMessages())
        self.assertEqual(
            ubuntu_translation.translations,
            upstream_translation.translations)

    def test_split_translations(self):
        """Split translations splits POTMsgSet and TranslationMessage."""
        splitter = self.makeTranslationSplitter()
        upstream_item, ubuntu_item = self.makeSharedPOTMsgSet(splitter)
        upstream_message = self.factory.makeCurrentTranslationMessage(
            potmsgset=upstream_item.potmsgset,
            potemplate=upstream_item.potemplate)
        splitter.split()
        self.assertNotEqual(
            list(upstream_item.potemplate), list(ubuntu_item.potemplate))
        self.assertNotEqual(
            list(upstream_item.potmsgset.getAllTranslationMessages()),
            list(ubuntu_item.potmsgset.getAllTranslationMessages()),
            )
        self.assertEqual(
            upstream_item.potmsgset.getAllTranslationMessages().count(),
            ubuntu_item.potmsgset.getAllTranslationMessages().count(),
        )

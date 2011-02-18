# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory
from lp.translations.interfaces.side import (
    TranslationSide,
    )
from lp.translations.translationsplitter import (
    TranslationSplitter,
    )


class TestTranslationSplitter(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

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
            self.factory.makeProductSeries(), self.factory.makeSourcePackage())

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

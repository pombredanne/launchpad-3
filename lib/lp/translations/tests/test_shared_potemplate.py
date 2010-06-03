# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0102

__metaclass__ = type

from storm.store import Store
import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing import ZopelessDatabaseLayer
from lp.testing import (record_statements, run_with_storm_debug,
    TestCaseWithFactory)
from lp.translations.interfaces.potemplate import IPOTemplateSet

class TestTranslationSharingPOTemplate(TestCaseWithFactory):
    """Test behaviour of "sharing" PO templates."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        """Set up context to test in."""
        # Create a product with two series and sharing POTemplates
        # in different series ('devel' and 'stable').
        super(TestTranslationSharingPOTemplate, self).setUp()
        self.foo = self.factory.makeProduct()
        self.foo_devel = self.factory.makeProductSeries(
            name='devel', product=self.foo)
        self.foo_stable = self.factory.makeProductSeries(
            name='stable', product=self.foo)
        self.foo.official_rosetta = True

        # POTemplate is a 'sharing' one if it has the same name ('messages').
        self.devel_potemplate = self.factory.makePOTemplate(
            productseries=self.foo_devel, name="messages")
        self.stable_potemplate = self.factory.makePOTemplate(
            self.foo_stable, name="messages")

        # Create a single POTMsgSet that is used across all tests,
        # and add it to only one of the POTemplates.
        self.potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate)
        self.potmsgset.setSequence(self.devel_potemplate, 1)

    def test_getPOTMsgSets(self):
        self.potmsgset.setSequence(self.stable_potemplate, 1)

        devel_potmsgsets = list(self.devel_potemplate.getPOTMsgSets())
        stable_potmsgsets = list(self.stable_potemplate.getPOTMsgSets())

        self.assertEquals(devel_potmsgsets, [self.potmsgset])
        self.assertEquals(devel_potmsgsets, stable_potmsgsets)

    def test_getPOTMsgSetByMsgIDText(self):
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate,
                                               singular="Open file",
                                               sequence=2)

        # We can retrieve the potmsgset by its ID text.
        read_potmsgset = self.devel_potemplate.getPOTMsgSetByMsgIDText(
            "Open file")
        self.assertEquals(potmsgset, read_potmsgset)

    def test_getPOTMsgSetBySequence(self):
        sequence = 2
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate,
                                               sequence=sequence)

        # We can retrieve the potmsgset by its sequence.
        read_potmsgset = self.devel_potemplate.getPOTMsgSetBySequence(
            sequence)
        self.assertEquals(potmsgset, read_potmsgset)

        # It's still not present in different sharing PO template.
        read_potmsgset = self.stable_potemplate.getPOTMsgSetBySequence(
            sequence)
        self.assertEquals(read_potmsgset, None)

    def test_getPOTMsgSetByID(self):
        potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate,
                                               sequence=3)
        id = potmsgset.id

        # We can retrieve the potmsgset by its ID.
        read_potmsgset = self.devel_potemplate.getPOTMsgSetByID(id)
        self.assertEquals(potmsgset, read_potmsgset)

        # Getting this one in a different template doesn't work.
        read_potmsgset = self.stable_potemplate.getPOTMsgSetByID(id)
        self.assertEquals(read_potmsgset, None)

        # Nor can you get an entry with a made up ID.
        random_id = 100000 + self.factory.getUniqueInteger()
        read_potmsgset = self.devel_potemplate.getPOTMsgSetByID(random_id)
        self.assertEquals(read_potmsgset, None)

    def test_hasMessageID(self):
        naked_potemplate = removeSecurityProxy(self.devel_potemplate)
        # Let's get details we need for a POTMsgSet that is
        # already in the POTemplate.
        present_msgid_singular = self.potmsgset.msgid_singular
        present_msgid_plural = self.potmsgset.msgid_plural
        present_context = self.potmsgset.context
        has_message_id = naked_potemplate.hasMessageID(
            present_msgid_singular, present_msgid_plural, present_context)
        self.assertEquals(has_message_id, True)

    def test_hasPluralMessage(self):
        naked_potemplate = removeSecurityProxy(self.devel_potemplate)

        # At the moment, a POTemplate has no plural form messages.
        self.assertEquals(self.devel_potemplate.hasPluralMessage(), False)

        # Let's add a POTMsgSet with plural forms.
        plural_potmsgset = self.factory.makePOTMsgSet(self.devel_potemplate,
                                                      singular="singular",
                                                      plural="plural")
        plural_potmsgset.setSequence(self.devel_potemplate, 4)

        # Now, template contains a plural form message.
        self.assertEquals(self.devel_potemplate.hasPluralMessage(), True)

    def test_expireAllMessages(self):
        devel_potmsgsets = list(self.devel_potemplate.getPOTMsgSets())
        self.assertEquals(len(devel_potmsgsets) > 0, True)

        # Expiring all messages brings the count back to zero.
        self.devel_potemplate.expireAllMessages()
        devel_potmsgsets = list(self.devel_potemplate.getPOTMsgSets())
        self.assertEquals(len(devel_potmsgsets), 0)

        # Expiring all messages even when all are already expired still works.
        self.devel_potemplate.expireAllMessages()
        devel_potmsgsets = list(self.devel_potemplate.getPOTMsgSets())
        self.assertEquals(len(devel_potmsgsets), 0)

    def test_createPOTMsgSetFromMsgIDs(self):
        # We need a 'naked' potemplate to make use of getOrCreatePOMsgID
        # private method.
        naked_potemplate = removeSecurityProxy(self.devel_potemplate)

        # Let's create a new POTMsgSet.
        singular_text = self.factory.getUniqueString()
        msgid_singular = naked_potemplate.getOrCreatePOMsgID(singular_text)
        potmsgset = self.devel_potemplate.createPOTMsgSetFromMsgIDs(
            msgid_singular=msgid_singular)
        self.assertEquals(potmsgset.msgid_singular, msgid_singular)

        # And let's add it to the devel_potemplate.
        potmsgset.setSequence(self.devel_potemplate, 5)
        devel_potmsgsets = list(self.devel_potemplate.getPOTMsgSets())
        self.assertEquals(len(devel_potmsgsets), 2)

        # Creating it with a different context also works.
        msgid_context = self.factory.getUniqueString()
        potmsgset_context = self.devel_potemplate.createPOTMsgSetFromMsgIDs(
            msgid_singular=msgid_singular, context=msgid_context)
        self.assertEquals(potmsgset_context.msgid_singular, msgid_singular)
        self.assertEquals(potmsgset_context.context, msgid_context)

    def test_getOrCreateSharedPOTMsgSet(self):
        # Let's create a new POTMsgSet.
        singular_text = self.factory.getUniqueString()
        potmsgset = self.devel_potemplate.getOrCreateSharedPOTMsgSet(
            singular_text, None)

        # If we try to add a POTMsgSet with identical strings,
        # we get back the existing one.
        same_potmsgset = self.devel_potemplate.getOrCreateSharedPOTMsgSet(
            singular_text, None)
        self.assertEquals(potmsgset, same_potmsgset)

        # And even if we do it in the shared template, existing
        # POTMsgSet is returned.
        shared_potmsgset = self.stable_potemplate.getOrCreateSharedPOTMsgSet(
            singular_text, None)
        self.assertEquals(potmsgset, shared_potmsgset)


class TestMessageSharingProductPackage(TestCaseWithFactory):
    """Test message sharing between a product and a package."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestMessageSharingProductPackage, self).setUp()

        self.ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.hoary = self.ubuntu['hoary']
        self.warty = self.ubuntu['warty']
        self.ubuntu.translation_focus = self.hoary
        self.packagename = self.factory.makeSourcePackageName()

        self.product = self.factory.makeProduct()
        self.trunk = self.product.getSeries('trunk')
        self.stable = self.factory.makeProductSeries(
            product=self.product)

        self.templatename = self.factory.getUniqueString()
        self.trunk_template = self.factory.makePOTemplate(
            productseries=self.trunk, name=self.templatename)
        self.hoary_template = self.factory.makePOTemplate(
            distroseries=self.hoary, sourcepackagename=self.packagename,
            name=self.templatename)

        self.owner = self.factory.makePerson()
        self.potemplateset = getUtility(IPOTemplateSet)

    def _count_statements(self, iter):
        templates, statements = record_statements(list, iter)
        print "\nNumber of statements:", len(statements)
        return templates

    def test_getSharingPOTemplates_product(self):
        # Sharing templates for a product include the same templates from
        # a linked source package.
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=self.packagename,
            distroseries=self.hoary)
        self.trunk.setPackaging(self.hoary, self.packagename, self.owner)
        subset = self.potemplateset.getSharingSubset(product=self.product)
        templates = self._count_statements(
            subset.getSharingPOTemplates(self.templatename))

        self.assertContentEqual(
            [self.trunk_template, self.hoary_template], templates)

    def test_getSharingPOTemplates_package(self):
        # Sharing templates for a source package include the same templates 
        # from a linked product.
        sourcepackage = self.factory.makeSourcePackage(
            self.packagename, self.hoary)
        sourcepackage.setPackaging(self.trunk, self.owner)
        subset = self.potemplateset.getSharingSubset(
            distribution=self.hoary.distribution,
            sourcepackagename=self.packagename)
        templates = self._count_statements(
            subset.getSharingPOTemplates(self.templatename))

        self.assertContentEqual(
            [self.trunk_template, self.hoary_template], templates)

    def test_getSharingPOTemplates_product_multiple_series(self):
        # Sharing templates for a product include the same templates from
        # a linked source package, even with multiple series.
        stable_template = self.factory.makePOTemplate(
            productseries=self.stable, name=self.templatename)
        warty_template = self.factory.makePOTemplate(
            distroseries=self.warty, sourcepackagename=self.packagename,
            name=self.templatename)
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=self.packagename,
            distroseries=self.hoary)
        self.trunk.setPackaging(self.hoary, self.packagename, self.owner)
        subset = self.potemplateset.getSharingSubset(product=self.product)
        templates = self._count_statements(
            subset.getSharingPOTemplates(self.templatename))

        self.assertContentEqual(
            [self.trunk_template, self.hoary_template,
             stable_template, warty_template],
            templates)

    def test_getSharingPOTemplates_package_multiple_series(self):
        # Sharing templates for a source package include the same templates 
        # from a linked product, even with multiple series.
        stable_template = self.factory.makePOTemplate(
            productseries=self.stable, name=self.templatename)
        warty_template = self.factory.makePOTemplate(
            distroseries=self.warty, sourcepackagename=self.packagename,
            name=self.templatename)
        sourcepackage = self.factory.makeSourcePackage(
            self.packagename, self.hoary)
        sourcepackage.setPackaging(self.trunk, self.owner)
        subset = self.potemplateset.getSharingSubset(
            distribution=self.hoary.distribution,
            sourcepackagename=self.packagename)
        templates = self._count_statements(
            subset.getSharingPOTemplates(self.templatename))

        self.assertContentEqual(
            [self.trunk_template, self.hoary_template,
             stable_template, warty_template],
            templates)

    def test_getSharingPOTemplates_package_name_changed(self):
        # When the name of a package changes (but not the name of the
        # template), it will still share translations if it is linked
        # to the same product.
        changed_name = self.factory.makeSourcePackageName()
        warty_template = self.factory.makePOTemplate(
            distroseries=self.warty, sourcepackagename=changed_name,
            name=self.templatename)
        hoary_sourcepackage = self.factory.makeSourcePackage(
            self.packagename, self.hoary)
        hoary_sourcepackage.setPackaging(self.trunk, self.owner)
        warty_sourcepackage = self.factory.makeSourcePackage(
            changed_name, self.warty)
        warty_sourcepackage.setPackaging(self.stable, self.owner)
        subset = self.potemplateset.getSharingSubset(
            distribution=self.hoary.distribution,
            sourcepackagename=self.packagename)
        templates = self._count_statements(
            subset.getSharingPOTemplates(self.templatename))

        self.assertContentEqual(
            [self.trunk_template, self.hoary_template, warty_template],
            templates)

    def test_getSharingPOTemplates_many_series(self):
        # The number of queries for a call to getSharingPOTemplates must
        # remain constant.

        all_templates = [self.trunk_template, self.hoary_template]
        # Add a greater number of series and sharing templates on either side.
        for series_name in ('0.1', '0.2', '0.3', '0.4', '0.5', '0.6'):
            series = self.factory.makeProductSeries(self.product, series_name)
            all_templates.append(self.factory.makePOTemplate(
                productseries=series, name=self.templatename))
        distroseries_names = (
            'feisty', 'gutsy', 'hardy', 'intrepid', 'jaunty', 'karmic')
        for series_name in distroseries_names:
            series = self.factory.makeDistroSeries(
                self.ubuntu, name=series_name)
            all_templates.append(self.factory.makePOTemplate(
                distroseries=series, sourcepackagename=self.packagename,
                name=self.templatename))
        all_templates.append(self.factory.makePOTemplate(
            productseries=self.stable, name=self.templatename))
        all_templates.append(self.factory.makePOTemplate(
            distroseries=self.warty, sourcepackagename=self.packagename,
            name=self.templatename))
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=self.packagename,
            distroseries=self.hoary)
        self.trunk.setPackaging(self.hoary, self.packagename, self.owner)

        # Looking from the product side.
        subset = self.potemplateset.getSharingSubset(product=self.product)
        templates = self._count_statements(
            subset.getSharingPOTemplates(self.templatename))
        self.assertContentEqual(all_templates, templates)

        # Looking from the sourcepackage side.
        subset = self.potemplateset.getSharingSubset(
            distribution=self.hoary.distribution,
            sourcepackagename=self.packagename)
        templates = self._count_statements(
            subset.getSharingPOTemplates(self.templatename))
        self.assertContentEqual(all_templates, templates)

    def test_getSharingPOTemplates_product_unrelated_templates(self):
        # Sharing templates for a product must not include other templates
        # from a linked source package.
        self.factory.makePOTemplate(
            distroseries=self.hoary, sourcepackagename=self.packagename,
            name=self.factory.getUniqueString())
        self.factory.makePOTemplate(
            distroseries=self.warty, sourcepackagename=self.packagename,
            name=self.factory.getUniqueString())
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=self.packagename,
            distroseries=self.hoary)
        self.trunk.setPackaging(self.hoary, self.packagename, self.owner)
        subset = self.potemplateset.getSharingSubset(product=self.product)
        templates = self._count_statements(
            subset.getSharingPOTemplates(self.templatename))

        self.assertContentEqual(
            [self.trunk_template, self.hoary_template],
            templates)

    def test_getSharingPOTemplates_product_different_names_and_series(self):
        # A product may be packaged into differently named packages in
        # different distroseries.
        warty_packagename = self.factory.makeSourcePackageName()
        warty_template = self.factory.makePOTemplate(
            distroseries=self.warty, sourcepackagename=warty_packagename,
            name=self.templatename)
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=self.packagename,
            distroseries=self.hoary)
        self.trunk.setPackaging(self.hoary, self.packagename, self.owner)
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=warty_packagename,
            distroseries=self.warty)
        self.trunk.setPackaging(self.warty, warty_packagename, self.owner)
        subset = self.potemplateset.getSharingSubset(product=self.product)
        templates = self._count_statements(
            subset.getSharingPOTemplates(self.templatename))

        self.assertContentEqual(
            [self.trunk_template, self.hoary_template, warty_template],
            templates)

    def test_getSharingPOTemplates_product_different_names_same_series(self):
        # A product may be packaged into differently named packages even in
        # the same distroseries.
        other_packagename = self.factory.makeSourcePackageName()
        other_template = self.factory.makePOTemplate(
            distroseries=self.warty, sourcepackagename=other_packagename,
            name=self.templatename)
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=self.packagename,
            distroseries=self.hoary)
        self.trunk.setPackaging(self.hoary, self.packagename, self.owner)
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=other_packagename,
            distroseries=self.hoary)
        self.trunk.setPackaging(self.hoary, other_packagename, self.owner)
        subset = self.potemplateset.getSharingSubset(product=self.product)
        templates = self._count_statements(
            subset.getSharingPOTemplates(self.templatename))

        self.assertContentEqual(
            [self.trunk_template, self.hoary_template, other_template],
            templates)

    def test_getSharingPOTemplates_package_unrelated_template(self):
        # Sharing templates for a source package must not include other
        # templates from a linked product.
        self.factory.makePOTemplate(
            productseries=self.trunk, name=self.factory.getUniqueString())
        self.factory.makePOTemplate(
            productseries=self.stable, name=self.factory.getUniqueString())
        sourcepackage = self.factory.makeSourcePackage(
            self.packagename, self.hoary)
        sourcepackage.setPackaging(self.trunk, self.owner)
        subset = self.potemplateset.getSharingSubset(
            distribution=self.hoary.distribution,
            sourcepackagename=self.packagename)
        templates = self._count_statements(
            subset.getSharingPOTemplates(self.templatename))

        self.assertContentEqual(
            [self.trunk_template, self.hoary_template],
            templates)

    def test_getSharingPOTemplates_package_only(self):
        # Sharing templates for a source package only, is done by the 
        # sourcepackagename.
        warty_template = self.factory.makePOTemplate(
            distroseries=self.warty, sourcepackagename=self.packagename,
            name=self.templatename)
        other_series = self.factory.makeDistroSeries(self.ubuntu)
        other_template = self.factory.makePOTemplate(
            distroseries=other_series, sourcepackagename=self.packagename,
            name=self.templatename)
        subset = self.potemplateset.getSharingSubset(
            distribution=self.hoary.distribution,
            sourcepackagename=self.packagename)
        templates = self._count_statements(
            subset.getSharingPOTemplates(self.templatename))

        self.assertContentEqual(
            [self.hoary_template, other_template, warty_template], templates)

    def test_getSharingPOTemplates_package_one_linked(self):
        # Once one sourcepackage is linked to a product, no sharing by name
        # is possible anymore. Only the linked package will share with the
        # product.
        warty_template = self.factory.makePOTemplate(
            distroseries=self.warty, sourcepackagename=self.packagename,
            name=self.templatename)
        other_series = self.factory.makeDistroSeries(self.ubuntu)
        other_template = self.factory.makePOTemplate(
            distroseries=other_series, sourcepackagename=self.packagename,
            name=self.templatename)

        hoary_sourcepackage = self.factory.makeSourcePackage(
            self.templatename, self.hoary)
        hoary_sourcepackage.setPackaging(self.trunk, self.owner)

        # The sharing subset for the linked package.
        subset = self.potemplateset.getSharingSubset(
            distribution=self.hoary.distribution,
            sourcepackagename=self.packagename)
        templates = self._count_statements(
            subset.getSharingPOTemplates(self.templatename))

        self.assertContentEqual(
            [self.hoary_template, self.trunk_template], templates)

        # The subset for the not linked package. No sharing templates.
        subset = self.potemplateset.getSharingSubset(
            distribution=self.warty.distribution,
            sourcepackagename=self.packagename)
        templates = self._count_statements(
            subset.getSharingPOTemplates(self.templatename))

        self.assertEqual([], templates)

    def test_getOrCreateSharedPOTMsgSet_product(self):
        # Trying to create an identical POTMsgSet in a product as exists
        # in a linked sourcepackage will return the existing POTMsgset.
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=self.packagename,
            distroseries=self.hoary)
        self.trunk.setPackaging(self.hoary, self.packagename, self.owner)
        hoary_potmsgset = self.factory.makePOTMsgSet(
            potemplate=self.hoary_template, sequence=1)

        trunk_potmsgset = self.trunk_template.getOrCreateSharedPOTMsgSet(
                singular_text=hoary_potmsgset.singular_text,
                plural_text=hoary_potmsgset.plural_text)
        self.assertEqual(hoary_potmsgset, trunk_potmsgset)

    def test_getOrCreateSharedPOTMsgSet_package(self):
        # Trying to create an identical POTMsgSet in a product as exists
        # in a linked sourcepackage will return the existing POTMsgset.
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=self.packagename,
            distroseries=self.hoary)
        self.trunk.setPackaging(self.hoary, self.packagename, self.owner)
        hoary_potmsgset = self.factory.makePOTMsgSet(
            potemplate=self.hoary_template, sequence=1)

        trunk_potmsgset = self.trunk_template.getOrCreateSharedPOTMsgSet(
                singular_text=hoary_potmsgset.singular_text,
                plural_text=hoary_potmsgset.plural_text)
        self.assertEqual(hoary_potmsgset, trunk_potmsgset)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

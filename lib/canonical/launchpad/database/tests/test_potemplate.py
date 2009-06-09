# Copyright 2008-2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from unittest import TestLoader

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.database.potemplate import POTemplateSet
from canonical.launchpad.interfaces import (
    ILanguageSet, IPOTemplateSet)
from canonical.testing import DatabaseFunctionalLayer
from lp.registry.interfaces.distribution import IDistributionSet
from lp.testing import TestCaseWithFactory


class TestPOTemplate(TestCaseWithFactory):
    """Test POTemplate functions not covered by doctests."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.potemplate = removeSecurityProxy(self.factory.makePOTemplate(
            translation_domain = "testdomain"))

    def test_composePOFilePath(self):
        esperanto = getUtility(ILanguageSet).getLanguageByCode('eo')
        self.potemplate.path = "testdir/messages.pot"
        expected = "testdir/testdomain-eo.po"
        result = self.potemplate._composePOFilePath(esperanto)
        self.failUnlessEqual(expected, result,
            "_composePOFilePath does not create a correct file name with "
            "directory and language code. "
            "(Expected: '%s' Got: '%s')" % (expected, result)
            )

        self.potemplate.path = "testdir/messages.pot"
        expected = "testdir/testdomain-eo@VARIANT.po"
        result = self.potemplate._composePOFilePath(esperanto, 'VARIANT')
        self.failUnlessEqual(expected, result,
            "_composePOFilePath does not create a correct file name with "
            "directory, language code and variant. "
            "(Expected: '%s' Got: '%s')" % (expected, result)
            )

        self.potemplate.path = "/messages.pot"
        expected = "/testdomain-eo.po"
        result = self.potemplate._composePOFilePath(esperanto)
        self.failUnlessEqual(expected, result,
            "_composePOFilePath does not create a correct file name with "
            "leading slash and language code. "
            "(Expected: '%s' Got: '%s')" % (expected, result)
            )

        self.potemplate.path = "messages.pot"
        expected = "testdomain-eo.po"
        result = self.potemplate._composePOFilePath(esperanto)
        self.failUnlessEqual(expected, result,
            "_composePOFilePath does not create a correct file name with "
            "missing directory and language code. "
            "(Expected: '%s' Got: '%s')" % (expected, result)
            )


class EquivalenceClassTestMixin:
    """Helper for POTemplate equivalence class tests."""
    def _compareResult(self, expected, actual):
        """Compare equivalence-classes set to expectations.

        This ignores the ordering of templates in an equivalence class.
        A separate test looks at ordering.
        """
        self.assertEqual(set(actual.iterkeys()), set(expected.iterkeys()))
        for key, value in actual.iteritems():
            self.assertEqual(set(value), set(expected[key]))


class TestProductTemplateEquivalenceClasses(TestCaseWithFactory,
                                            EquivalenceClassTestMixin):
    """Which templates in Products will and will not share messages."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProductTemplateEquivalenceClasses, self).setUp()
        self.product = self.factory.makeProduct()
        self.trunk = self.product.getSeries('trunk')
        self.stable = self.factory.makeProductSeries(
            product=self.product)
        self.find_potemplate_equivalence_classes_for = getUtility(
            IPOTemplateSet).findPOTemplateEquivalenceClassesFor

    def test_ProductTemplateEquivalence(self):
        # Within a product, two identically named templates form an
        # equivalence class.
        trunk_template = self.factory.makePOTemplate(
            productseries=self.trunk, name='foo')
        stable_template = self.factory.makePOTemplate(
            productseries=self.stable, name='foo')

        classes = self.find_potemplate_equivalence_classes_for(
            product=self.product)
        expected = { ('foo', None): [trunk_template, stable_template] }
        self._compareResult(expected, classes)

    def test_DifferentlyNamedProductTemplatesAreNotEquivalent(self):
        # Two differently-named templates in a product do not form an
        # equivalence class.
        trunk_template = self.factory.makePOTemplate(
            productseries=self.trunk, name='foo')
        stable_template = self.factory.makePOTemplate(
            productseries=self.stable, name='bar')

        classes = self.find_potemplate_equivalence_classes_for(
            product=self.product)
        expected = {
            ('foo', None): [trunk_template],
            ('bar', None): [stable_template],
        }
        self._compareResult(expected, classes)

    def test_NoEquivalenceAcrossProducts(self):
        # Two identically-named templates in different products do not
        # form an equivalence class.
        external_series = self.factory.makeProductSeries()
        template1 = self.factory.makePOTemplate(
            productseries=self.trunk, name='foo')
        template2 = self.factory.makePOTemplate(
            productseries=external_series, name='foo')

        classes = self.find_potemplate_equivalence_classes_for(
            product=self.product)
        expected = { ('foo', None): [template1] }
        self._compareResult(expected, classes)

        classes = self.find_potemplate_equivalence_classes_for(
            product=external_series.product)
        expected = { ('foo', None): [template2] }
        self._compareResult(expected, classes)


class TestDistroTemplateEquivalenceClasses(TestCaseWithFactory,
                                           EquivalenceClassTestMixin):
    """Which templates in Distributions will and will not share messages."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDistroTemplateEquivalenceClasses, self).setUp()
        self.ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        self.hoary = self.ubuntu['hoary']
        self.warty = self.ubuntu['warty']
        self.package = self.factory.makeSourcePackageName()
        self.find_potemplate_equivalence_classes_for = getUtility(
            IPOTemplateSet).findPOTemplateEquivalenceClassesFor

    def test_PackageTemplateEquivalence(self):
        # Two identically-named templates in the same source package in
        # different releases of the same distribution form an
        # equivalence class.
        hoary_template = self.factory.makePOTemplate(
            distroseries=self.hoary, sourcepackagename=self.package,
            name='foo')
        warty_template = self.factory.makePOTemplate(
            distroseries=self.warty, sourcepackagename=self.package,
            name='foo')

        classes = self.find_potemplate_equivalence_classes_for(
            distribution=self.ubuntu, sourcepackagename=self.package)

        expected = {
            ('foo', self.package.name): [hoary_template, warty_template],
        }
        self._compareResult(expected, classes)

    def test_DifferentlyNamedDistroTemplatesAreNotEquivalent(self):
        # Two differently-named templates in a distribution package do
        # not form an equivalence class.
        hoary_template = self.factory.makePOTemplate(
            distroseries=self.hoary, sourcepackagename=self.package,
            name='foo')
        warty_template = self.factory.makePOTemplate(
            distroseries=self.warty, sourcepackagename=self.package,
            name='bar')

        classes = self.find_potemplate_equivalence_classes_for(
            distribution=self.ubuntu, sourcepackagename=self.package)

        expected = {
            ('foo', self.package.name): [hoary_template],
            ('bar', self.package.name): [warty_template],
        }
        self._compareResult(expected, classes)

    def test_NoEquivalenceAcrossPackages(self):
        # Two identically-named templates in the same distribution do
        # not form an equivalence class if they don't have the same
        # source package name.
        other_package = self.factory.makeSourcePackageName()
        our_template = self.factory.makePOTemplate(
            distroseries=self.hoary, sourcepackagename=self.package,
            name='foo')
        other_template = self.factory.makePOTemplate(
            distroseries=self.warty, sourcepackagename=other_package,
            name='foo')

        classes = self.find_potemplate_equivalence_classes_for(
            distribution=self.ubuntu)

        self.assertTrue(('foo', self.package.name) in classes)
        self.assertEqual(classes[('foo', self.package.name)], [our_template])
        self.assertTrue(('foo', other_package.name) in classes)
        self.assertEqual(
            classes[('foo', other_package.name)], [other_template])

    def test_EquivalenceByNamePattern(self):
        # We can obtain equivalence classes for a distribution by
        # template name pattern.
        unique_name = (
            'krungthepmahanakornamornrattanakosinmahintaramahadilok-etc')
        bangkok_template = self.factory.makePOTemplate(
            distroseries=self.hoary, sourcepackagename=self.package,
            name=unique_name)

        classes = self.find_potemplate_equivalence_classes_for(
            distribution=self.ubuntu,
            name_pattern='krungthepmahanakorn.*-etc')

        expected = {
            (unique_name, self.package.name): [bangkok_template],
        }
        self._compareResult(expected, classes)


class TestTemplatePrecedence(TestCaseWithFactory):
    """Which of a set of "equivalent" `POTMsgSet`s is "representative." """
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestTemplatePrecedence, self).setUp(user='mark@hbd.com')
        self.product = self.factory.makeProduct()
        self.product.official_rosetta = True
        self.trunk = self.product.getSeries('trunk')
        self.one_dot_oh = self.factory.makeProductSeries(
            product=self.product, name='one')
        self.two_dot_oh = self.factory.makeProductSeries(
            product=self.product, name='two')
        self.trunk_template = self.factory.makePOTemplate(
            productseries=self.trunk, name='trunk')
        self.one_dot_oh_template = self.factory.makePOTemplate(
            productseries=self.one_dot_oh, name='one')
        self.two_dot_oh_template = self.factory.makePOTemplate(
            productseries=self.two_dot_oh, name='two')

        self.templates = [
            self.trunk_template,
            self.one_dot_oh_template,
            self.two_dot_oh_template,
            ]

        # Make sure there's another current template for every series.
        # This is to make sure that we can disable the templates we
        # care about without Product.primary_translatable ever falling
        # back on a different series and confusing our test.
        for template in self.templates:
            self.factory.makePOTemplate(productseries=template.productseries)

        self._setTranslationFocus(self.trunk)

    def _setTranslationFocus(self, focus_series):
        """Set focus_series as translation focus."""
        self.product.development_focus = focus_series
        self.assertEqual(self.product.primary_translatable, focus_series)

    def _sortTemplates(self, templates=None):
        """Order templates by precedence."""
        if templates is None:
            templates = self.templates
        return sorted(templates, cmp=POTemplateSet.getPOTemplatePrecedence)

    def _getPrimaryTemplate(self, templates=None):
        """Get first template in order of precedence."""
        return self._sortTemplates(templates)[0]

    def _enableTemplates(self, enable):
        """Set iscurrent flag for all templates."""
        for template in self.templates:
            template.iscurrent = enable

    def test_disabledTemplatesComeLast(self):
        # A disabled (non-current) template comes after a current one.
        candidates = [self.one_dot_oh_template, self.two_dot_oh_template]

        self.one_dot_oh_template.iscurrent = False
        self.assertEqual(
            self._getPrimaryTemplate(candidates), self.two_dot_oh_template)

        # This goes both ways, regardless of any other ordering the two
        # templates may have.
        self.one_dot_oh_template.iscurrent = True
        self.two_dot_oh_template.iscurrent = False
        self.assertEqual(
            self._getPrimaryTemplate(candidates), self.one_dot_oh_template)

    def test_focusSeriesComesFirst(self):
        # Unless disabled, a template with translation focus always
        # comes first.
        self.assertEqual(self._getPrimaryTemplate(), self.trunk_template)

        # This is the case regardless of any other ordering there
        # may be between the templates.
        self._setTranslationFocus(self.one_dot_oh)
        self.assertEqual(self._getPrimaryTemplate(), self.one_dot_oh_template)
        self._setTranslationFocus(self.two_dot_oh)
        self.assertEqual(self._getPrimaryTemplate(), self.two_dot_oh_template)

    def test_disabledTemplateComesLastDespiteFocus(self):
        # A disabled template comes after an enabled one regardless of
        # translation focus.
        self.trunk_template.iscurrent = False
        self.assertNotEqual(self._getPrimaryTemplate(), self.trunk_template)

    def test_disabledFocusBeatsOtherDisabledTemplate(self):
        # A disabled template with translation focus comes before
        # another disabled template.
        self._enableTemplates(False)
        self.assertEqual(self._getPrimaryTemplate(), self.trunk_template)

        # Both ways, regardless of any other ordering they may have.
        self._setTranslationFocus(self.one_dot_oh)
        self.assertEqual(self._getPrimaryTemplate(), self.one_dot_oh_template)

    def test_ageBreaksTie(self):
        # Of two templates that are both enabled but don't have
        # translation focus, the newest one (by id) has precedence.
        candidates = [self.one_dot_oh_template, self.two_dot_oh_template]
        self.assertEqual(
            self._getPrimaryTemplate(candidates), self.two_dot_oh_template)

    def test_ageBreaksTieWhenDisabled(self):
        # Age also acts as a tie-breaker between disabled templates.
        self._enableTemplates(False)
        self.test_ageBreaksTie()


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

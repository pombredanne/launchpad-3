# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from canonical.testing import ZopelessDatabaseLayer
from lp.translations.interfaces.potemplate import IHasTranslationTemplates
from lp.testing import TestCaseWithFactory, verifyObject


class HasTranslationTemplatesMixin(TestCaseWithFactory):
    """Test behaviour of objects with translation templates."""

    layer = ZopelessDatabaseLayer

    def setUp(self):
        # Create a product with two series and a shared POTemplate
        # in different series ('devel' and 'stable').
        super(HasTranslationTemplatesMixin, self).setUp()

    def createTranslationTemplate(self, name, priority=0):
        """Attaches a template to appropriate container."""
        raise NotImplementedError(
            'This must be provided by an executable test.')

    def test_implements_interface(self):
        # Make sure container implements IHasTranslationTemplates.
        verifyObject(IHasTranslationTemplates, self.container)

    def test_getCurrentTranslationTemplates(self):
        # With no current templates, we get an empty result set.
        results = self.container.getCurrentTranslationTemplates()
        current_templates = list(results)
        self.assertEquals([], current_templates)
        self.assertFalse(bool(results.any()))

        # With one of the templates marked as current, it is returned.
        template1 = self.createTranslationTemplate("one", priority=1)
        current_templates = list(
            self.container.getCurrentTranslationTemplates())
        self.assertEquals([template1], current_templates)

        # With two current templates, they are sorted by priority,
        # with higher numbers representing higher priority.
        template2 = self.createTranslationTemplate("two", priority=2)
        current_templates = list(
            self.container.getCurrentTranslationTemplates())
        self.assertEquals([template2, template1], current_templates)

        # Adding an obsolete template changes nothing.
        template3 = self.createTranslationTemplate("obsolete")
        template3.iscurrent = False
        current_templates = list(
            self.container.getCurrentTranslationTemplates())
        self.assertEquals([template2, template1], current_templates)

    def test_getCurrentTranslationTemplates_ids(self):
        # Returning just IDs works fine as well.
        template1 = self.createTranslationTemplate("one", priority=1)
        template2 = self.createTranslationTemplate("two", priority=2)
        current_templates_ids = list(
            self.container.getCurrentTranslationTemplates(just_ids=True))
        self.assertEquals(
            [template2.id, template1.id],
            current_templates_ids)

    def test_getCurrentTranslationFiles_empty(self):
        # With no current templates, we get an empty result set.
        current_translations = list(
            self.container.getCurrentTranslationFiles())
        self.assertEquals([], current_translations)

        # Even with one of the templates marked as current, nothing is
        # returned before POFile is added.
        template1 = self.createTranslationTemplate("one")
        current_translations = list(
            self.container.getCurrentTranslationFiles())
        self.assertEquals([], current_translations)

        # If template is not current, nothing is returned even if
        # there are POFiles attached to it.
        template1.iscurrent = False
        pofile = self.factory.makePOFile('sr', potemplate=template1)
        current_translations = list(
            self.container.getCurrentTranslationFiles())
        self.assertEquals([], current_translations)

    def test_getCurrentTranslationFiles_current(self):
        # If POFiles are attached to a current template, they are returned.
        template1 = self.createTranslationTemplate("one")
        pofile_sr = self.factory.makePOFile('sr', potemplate=template1)
        pofile_es = self.factory.makePOFile('es', potemplate=template1)
        # They are returned unordered, so we'll use a set over them
        # to make tests stable.
        current_translations = set(
            self.container.getCurrentTranslationFiles())
        self.assertEquals(
            set([pofile_sr, pofile_es]),
            current_translations)

        # All files, no matter what template they are in, are returned.
        template2 = self.createTranslationTemplate("two")
        pofile2_sr = self.factory.makePOFile('sr', potemplate=template2)
        current_translations = set(
            self.container.getCurrentTranslationFiles())
        self.assertEquals(
            set([pofile_sr, pofile_es, pofile2_sr]),
            current_translations)

        # If template is marked as obsolete, attached POFiles are
        # not returned anymore.
        template2.iscurrent = False
        current_translations = set(
            self.container.getCurrentTranslationFiles())
        self.assertEquals(
            set([pofile_sr, pofile_es]),
            current_translations)

    def test_getCurrentTranslationFiles_ids(self):
        # We can also fetch only IDs.
        template1 = self.createTranslationTemplate("one")
        pofile_sr = self.factory.makePOFile('sr', potemplate=template1)
        pofile_es = self.factory.makePOFile('es', potemplate=template1)
        current_translations_ids = set(
            self.container.getCurrentTranslationFiles(just_ids=True))
        self.assertEquals(
            set([pofile_sr.id, pofile_es.id]),
            current_translations_ids)


class TestProductSeries(HasTranslationTemplatesMixin):
    """Test implementation of IHasTranslationTemplates on ProductSeries."""

    def createTranslationTemplate(self, name, priority=0):
        potemplate = self.factory.makePOTemplate(
            name=name, productseries=self.container)
        potemplate.priority = priority
        return potemplate

    def setUp(self):
        super(TestProductSeries, self).setUp()
        self.container = self.factory.makeProductSeries()
        self.container.product.official_rosetta = True


class TestSourcePackage(HasTranslationTemplatesMixin):
    """Test implementation of IHasTranslationTemplates on ProductSeries."""

    def createTranslationTemplate(self, name, priority=0):
        potemplate = self.factory.makePOTemplate(
            name=name, distroseries=self.container.distroseries,
            sourcepackagename=self.container.sourcepackagename)
        potemplate.priority = priority
        return potemplate

    def setUp(self):
        super(TestSourcePackage, self).setUp()
        self.container = self.factory.makeSourcePackage()
        self.container.distroseries.distribution.official_rosetta = True


class TestDistroSeries(HasTranslationTemplatesMixin):
    """Test implementation of IHasTranslationTemplates on ProductSeries."""

    def createTranslationTemplate(self, name, priority=0):
        sourcepackage = self.factory.makeSourcePackage(
            distroseries=self.container)
        potemplate = self.factory.makePOTemplate(
            name=name, distroseries=self.container,
            sourcepackagename=sourcepackage.sourcepackagename)
        potemplate.priority = priority
        return potemplate

    def setUp(self):
        super(TestDistroSeries, self).setUp()
        self.container = self.factory.makeDistroRelease()
        self.container.distribution.official_rosetta = True


def test_suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestProductSeries))
    suite.addTest(loader.loadTestsFromTestCase(TestSourcePackage))
    suite.addTest(loader.loadTestsFromTestCase(TestDistroSeries))
    return suite

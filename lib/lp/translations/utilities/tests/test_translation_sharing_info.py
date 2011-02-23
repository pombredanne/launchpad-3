# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.testing.layers import ZopelessDatabaseLayer
from lp.testing import TestCaseWithFactory
from lp.translations.utilities.translationsharinginfo import (
    get_ubuntu_sharing_info,
    get_upstream_sharing_info,
    has_ubuntu_template,
    has_upstream_template,
    )


class TestTranslationSharingInfo(TestCaseWithFactory):
    """Tests for `get_upstream_sharing_info` and `get_ubuntu_sharing_info`"""

    layer = ZopelessDatabaseLayer

    def _makeSourcePackage(self):
        """Create an Ubuntu source package."""
        distroseries = self.factory.makeUbuntuDistroSeries()
        return self.factory.makeSourcePackage(distroseries=distroseries)

    def _makeUpstreamProductSeries(self, sourcepackage):
        """Create a product series and link it to the source package."""
        productseries = self.factory.makeProductSeries()
        self.factory.makePackagingLink(
            distroseries=sourcepackage.distroseries,
            sourcepackagename=sourcepackage.sourcepackagename,
            productseries=productseries)
        return productseries

    def test_no_upstream(self):
        # With no upstream the sharing information on a source package will
        # be empty.
        sourcepackage = self._makeSourcePackage()
        self.assertEquals(
            [],
            get_upstream_sharing_info(sourcepackage=sourcepackage))

    def test_no_upstream_with_name(self):
        # With no upstream the sharing information on a source package will
        # be empty, even when searching for a specific template name.
        sourcepackage = self._makeSourcePackage()
        templatename = self.factory.getUniqueString()
        self.assertEquals(
            [],
            get_upstream_sharing_info(
                sourcepackage=sourcepackage,
                templatename=templatename))

    def test_upstream_no_template(self):
        # With an upstream without a template the sharing information on a
        # source package will be empty.
        sourcepackage = self._makeSourcePackage()
        productseries = self._makeUpstreamProductSeries(sourcepackage)
        self.assertEquals(
            [(productseries, None)],
            get_upstream_sharing_info(sourcepackage=sourcepackage))

    def test_upstream_no_template_with_name(self):
        # With an upstream without a template the sharing information on a
        # source package will be empty, even when searching for a specific
        # template name.
        sourcepackage = self._makeSourcePackage()
        productseries = self._makeUpstreamProductSeries(sourcepackage)
        templatename = self.factory.getUniqueString()
        self.assertEquals(
            [(productseries, None)],
            get_upstream_sharing_info(
                sourcepackage=sourcepackage,
                templatename=templatename))

    def test_upstream_one_template(self):
        # With an upstream template the sharing information on a
        # source package will return that.
        sourcepackage = self._makeSourcePackage()
        productseries = self._makeUpstreamProductSeries(sourcepackage)
        potemplate = self.factory.makePOTemplate(productseries=productseries)
        self.assertEquals(
            [(productseries, potemplate)],
            get_upstream_sharing_info(sourcepackage=sourcepackage))

    def test_upstream_one_template_with_name(self):
        # With an upstream template the sharing information on a
        # source package will return that, even when searching for a
        # specific template name.
        sourcepackage = self._makeSourcePackage()
        productseries = self._makeUpstreamProductSeries(sourcepackage)
        templatename = self.factory.getUniqueString()
        potemplate = self.factory.makePOTemplate(
            productseries=productseries, name=templatename)
        self.assertEquals(
            [(productseries, potemplate)],
            get_upstream_sharing_info(
                sourcepackage=sourcepackage,
                templatename=templatename))

    def test_upstream_one_template_with_different_name(self):
        # With an upstream template the sharing information on a
        # source package will be empty if a different name is queried.
        sourcepackage = self._makeSourcePackage()
        productseries = self._makeUpstreamProductSeries(sourcepackage)
        templatename = self.factory.getUniqueString()
        self.factory.makePOTemplate(
            productseries=productseries, name=templatename)
        different_templatename = self.factory.getUniqueString()
        self.assertEquals(
            [(productseries, None)],
            get_upstream_sharing_info(
                sourcepackage=sourcepackage,
                templatename=different_templatename))

    def test_no_ubuntu(self):
        # With no sourcepackage the sharing information on a source package
        # will be empty.
        productseries = self.factory.makeProductSeries()
        self.assertEquals(
            [],
            get_ubuntu_sharing_info(productseries=productseries))

    def test_no_ubuntu_with_name(self):
        # With no sourcepackage the sharing information on a source package
        # will be empty, even when searching for a specific template name.
        productseries = self.factory.makeProductSeries()
        templatename = self.factory.getUniqueString()
        self.assertEquals(
            [],
            get_ubuntu_sharing_info(
                productseries=productseries, templatename=templatename))

    def test_ubuntu_no_template(self):
        # With a sourcepackage without a template the sharing information
        # on a productseries will be empty.
        sourcepackage = self._makeSourcePackage()
        productseries = self._makeUpstreamProductSeries(sourcepackage)
        self.assertEquals(
            [(sourcepackage, None)],
            get_ubuntu_sharing_info(productseries=productseries))

    def test_ubuntu_no_template_with_name(self):
        # With a sourcepackage without a template the sharing information
        # on a productseries will be empty, even when searching for a
        # specific template name.
        sourcepackage = self._makeSourcePackage()
        productseries = self._makeUpstreamProductSeries(sourcepackage)
        templatename = self.factory.getUniqueString()
        self.assertEquals(
            [(sourcepackage, None)],
            get_ubuntu_sharing_info(
                productseries=productseries, templatename=templatename))

    def test_ubuntu_one_template(self):
        # With a sourcepackage template the sharing information on a
        # source package will return that.
        sourcepackage = self._makeSourcePackage()
        productseries = self._makeUpstreamProductSeries(sourcepackage)
        potemplate = self.factory.makePOTemplate(sourcepackage=sourcepackage)
        self.assertEquals(
            [(sourcepackage, potemplate)],
            get_ubuntu_sharing_info(
                productseries=productseries))

    def test_ubuntu_one_template_with_name(self):
        # With a sourcepackage template the sharing information on a
        # productseries will return that, even when searching for a
        # specific template name.
        sourcepackage = self._makeSourcePackage()
        productseries = self._makeUpstreamProductSeries(sourcepackage)
        templatename = self.factory.getUniqueString()
        potemplate = self.factory.makePOTemplate(
            sourcepackage=sourcepackage,
            name=templatename)
        self.assertEquals(
            [(sourcepackage, potemplate)],
            get_ubuntu_sharing_info(
                productseries=productseries, templatename=templatename))

    def test_ubuntu_one_template_with_different_name(self):
        # With a sourcepackage template the sharing information on a
        # productseries will  be empty if a different name is queried.
        sourcepackage = self._makeSourcePackage()
        productseries = self._makeUpstreamProductSeries(sourcepackage)
        templatename = self.factory.getUniqueString()
        self.factory.makePOTemplate(
            sourcepackage=sourcepackage,
            name=templatename)
        different_templatename = self.factory.getUniqueString()
        self.assertEquals(
            [(sourcepackage, None)],
            get_ubuntu_sharing_info(
                productseries=productseries,
                templatename=different_templatename))

    def test_has_upstream_template_no_productseries(self):
        # Without an upstream project, no upstream templates won't be
        # available either.
        sourcepackage = self._makeSourcePackage()
        templatename = self.factory.getUniqueString()

        self.assertFalse(
            has_upstream_template(sourcepackage, templatename))

    def test_has_upstream_template_no_template(self):
        # No template exists on the upstream project.
        sourcepackage = self._makeSourcePackage()
        productseries = self._makeUpstreamProductSeries(sourcepackage)
        templatename = self.factory.getUniqueString()

        self.assertFalse(
            has_upstream_template(sourcepackage, templatename))

    def test_has_upstream_template_one_template(self):
        # There is one template on the upstream project that matches the
        # name.
        sourcepackage = self._makeSourcePackage()
        productseries = self._makeUpstreamProductSeries(sourcepackage)
        templatename = self.factory.getUniqueString()
        self.factory.makePOTemplate(
            productseries=productseries, name=templatename)

        self.assertTrue(
            has_upstream_template(sourcepackage, templatename))

    def test_has_upstream_template_one_template_wrong_name(self):
        # There is one template on the upstream project but it matches not
        # the requested name.
        sourcepackage = self._makeSourcePackage()
        productseries = self._makeUpstreamProductSeries(sourcepackage)
        self.factory.makePOTemplate(productseries=productseries)
        different_templatename = self.factory.getUniqueString()

        self.assertFalse(
            has_upstream_template(sourcepackage, different_templatename))

    def test_has_upstream_template_any_template(self):
        # There is one template on the upstream project, not specifying
        # a template name still indicates that there is a template.
        sourcepackage = self._makeSourcePackage()
        productseries = self._makeUpstreamProductSeries(sourcepackage)
        self.factory.makePOTemplate(productseries=productseries)

        self.assertTrue(has_upstream_template(sourcepackage))

    def test_has_upstream_template_any_template_none(self):
        # There is no template on the upstream project.
        sourcepackage = self._makeSourcePackage()
        self._makeUpstreamProductSeries(sourcepackage)

        self.assertFalse(has_upstream_template(sourcepackage))

    def test_has_ubuntu_template_no_sourcepackage(self):
        # There is no Ubuntu source package, so no Ubuntu template can be
        # found.
        productseries = self.factory.makeProductSeries()
        templatename = self.factory.getUniqueString()

        self.assertFalse(has_ubuntu_template(productseries, templatename))

    def test_has_ubuntu_template_no_template(self):
        # The Ubuntu source package has no template.
        sourcepackage = self._makeSourcePackage()
        productseries = self._makeUpstreamProductSeries(sourcepackage)
        templatename = self.factory.getUniqueString()

        self.assertFalse(has_ubuntu_template(productseries, templatename))

    def test_has_ubuntu_template_one_template(self):
        # There is one template on the Ubuntu source package that matches
        # the name.
        sourcepackage = self._makeSourcePackage()
        productseries = self._makeUpstreamProductSeries(sourcepackage)
        templatename = self.factory.getUniqueString()
        self.factory.makePOTemplate(
            sourcepackage=sourcepackage, name=templatename)

        self.assertTrue(has_ubuntu_template(productseries, templatename))

    def test_has_ubuntu_template_one_template_wrong_name(self):
        # There is one template on the Ubuntu source package but it matches
        # not the requested name.
        sourcepackage = self._makeSourcePackage()
        productseries = self._makeUpstreamProductSeries(sourcepackage=sourcepackage)
        templatename = self.factory.getUniqueString()
        self.factory.makePOTemplate(
            sourcepackage=sourcepackage, name=templatename)
        different_templatename = self.factory.getUniqueString()

        self.assertFalse(
            has_ubuntu_template(productseries, different_templatename))

    def test_has_ubuntu_template_any_template(self):
        # There is one template on the Ubuntu source package, not specifying
        # a template name still indicates that there is a template.
        sourcepackage= self._makeSourcePackage()
        productseries = self._makeUpstreamProductSeries(sourcepackage)
        self.factory.makePOTemplate(sourcepackage=sourcepackage)

        self.assertTrue(has_ubuntu_template(productseries))

    def test_has_ubuntu_template_any_template_none(self):
        # There is no template on the Ubuntu source package.
        sourcepackage = self._makeSourcePackage()
        productseries = self._makeUpstreamProductSeries(sourcepackage)

        self.assertFalse(has_ubuntu_template(productseries))

# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the POTemplate recipe view classes and templates."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.launchpad.testing.pages import (
    extract_text,
    find_tag_by_id,
    )
from lp.app.enums import ServiceUsage
from lp.services.features.testing import FeatureFixture
from lp.testing import (
    BrowserTestCase,
    celebrity_logged_in,
    )
from lp.translations.interfaces.side import TranslationSide


def set_translations_usage(obj):
    """Set the translations_usage to LAUNCHPAD."""
    with celebrity_logged_in('admin'):
        obj.translations_usage = ServiceUsage.LAUNCHPAD


def enable_translations_on_distroseries(distroseries):
    with celebrity_logged_in('admin'):
        distroseries.hide_all_translations = False


class TestSharingInfoMixin:
    """Test display of sharing info."""

    def makeNotSharingObject(self):
        """Create an object that is not sharing."""
        raise NotImplementedError

    NOT_SHARING_TEXT = None

    def makeSharingObject(self):
        """Create an object that is sharing."""
        raise NotImplementedError

    SHARING_TEXT = None

    def _test_sharing_information(self, obj, expected_text):
        self.useFixture(FeatureFixture(
            {'translations.sharing_information.enabled': 'on'}))
        browser = self.getViewBrowser(
            obj, no_login=True, rootsite="translations")
        sharing_info = find_tag_by_id(browser.contents, 'sharing-information')
        if expected_text is None:
            self.assertIs(None, sharing_info)
        else:
            self.assertIsNot(None, sharing_info)
            self.assertTextMatchesExpressionIgnoreWhitespace(
                expected_text, extract_text(sharing_info))

    def test_not_sharing(self):
        self._test_sharing_information(
            self.makeNotSharingObject(), self.NOT_SHARING_TEXT)

    def test_sharing(self):
        self._test_sharing_information(
            self.makeSharingObject(), self.SHARING_TEXT)


class TestUpstreamPOTemplateSharingInfo(BrowserTestCase,
                                        TestSharingInfoMixin):
    """Test display of template sharing info."""

    layer = DatabaseFunctionalLayer

    def makeNotSharingObject(self):
        return self.factory.makePOTemplate()

    NOT_SHARING_TEXT = """
        This template is not sharing translations with a template in an
        Ubuntu source package."""

    def makeSharingObject(self):
        template = self.factory.makePOTemplate()
        packaging = self.factory.makePackagingLink(
            productseries=template.productseries, in_ubuntu=True)
        self.factory.makePOTemplate(
            distroseries=packaging.distroseries,
            sourcepackagename=packaging.sourcepackagename,
            name=template.name)
        return template

    SHARING_TEXT = """
        This template is sharing translations with .*"""


class TestPOFileSharingInfo(BrowserTestCase,
                                        TestSharingInfoMixin):
    """Test display of POFile sharing info."""

    layer = DatabaseFunctionalLayer

    def makeNotSharingObject(self):
        return self.factory.makePOFile()

    NOT_SHARING_TEXT = None

    def makeSharingObject(self):
        pofile = self.factory.makePOFile()
        packaging = self.factory.makePackagingLink(
            productseries=pofile.potemplate.productseries,
            in_ubuntu=True)
        # This will also create a copy of pofile.
        self.factory.makePOTemplate(
            distroseries=packaging.distroseries,
            sourcepackagename=packaging.sourcepackagename,
            name=pofile.potemplate.name)
        return pofile

    SHARING_TEXT = """
        These translations are shared with .*"""


class TestUpstreamSharingInfo(BrowserTestCase, TestSharingInfoMixin):
    """Test display of product series sharing info."""

    layer = DatabaseFunctionalLayer

    def makeNotSharingObject(self):
        productseries = self.factory.makeProductSeries()
        set_translations_usage(productseries.product)
        return productseries

    NOT_SHARING_TEXT = """
        This project series is not sharing translations with an Ubuntu source
        package."""

    def makeSharingObject(self):
        template = self.factory.makePOTemplate()
        packaging = self.factory.makePackagingLink(
            productseries=template.productseries, in_ubuntu=True)
        self.factory.makePOTemplate(
            distroseries=packaging.distroseries,
            sourcepackagename=packaging.sourcepackagename,
            name=template.name)
        return template.productseries

    SHARING_TEXT = """
        This project series is sharing translations with .*"""


class TestUbuntuPOTemplateSharingInfo(BrowserTestCase, TestSharingInfoMixin):
    """Test display of template sharing info in an Ubuntu source package."""

    layer = DatabaseFunctionalLayer

    def makeNotSharingObject(self):
        template = self.factory.makePOTemplate(side=TranslationSide.UBUNTU)
        enable_translations_on_distroseries(template.distroseries)
        return template

    NOT_SHARING_TEXT = """
        This template is not sharing translations with a template in an
        upstream project."""

    def makeSharingObject(self):
        upstream_template = self.factory.makePOTemplate()
        packaging = self.factory.makePackagingLink(
            productseries=upstream_template.productseries, in_ubuntu=True)
        template = self.factory.makePOTemplate(
            distroseries=packaging.distroseries,
            sourcepackagename=packaging.sourcepackagename,
            name=upstream_template.name)
        enable_translations_on_distroseries(packaging.distroseries)
        return template

    SHARING_TEXT = """
        This template is sharing translations with .*"""


class TestUbuntuSharingInfo(BrowserTestCase, TestSharingInfoMixin):
    """Test display of source package sharing info."""

    layer = DatabaseFunctionalLayer

    def makeNotSharingObject(self):
        sourcepackage = self.factory.makeSourcePackage(
            distroseries=self.factory.makeUbuntuDistroSeries())
        enable_translations_on_distroseries(sourcepackage.distroseries)
        return sourcepackage

    NOT_SHARING_TEXT = """
        This source package is not sharing translations with an upstream
        project."""

    def makeSharingObject(self):
        upstream_template = self.factory.makePOTemplate()
        packaging = self.factory.makePackagingLink(
            productseries=upstream_template.productseries, in_ubuntu=True)
        self.factory.makePOTemplate(
            distroseries=packaging.distroseries,
            sourcepackagename=packaging.sourcepackagename,
            name=upstream_template.name)
        enable_translations_on_distroseries(packaging.distroseries)
        return packaging.sourcepackage

    SHARING_TEXT = """
        This source package is sharing translations with .*"""

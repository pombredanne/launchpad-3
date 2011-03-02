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

    def _makePackagingAndTemplates(self, side):
        """Create a packaging links and the templates on each side of it.

        Returns the template for the requested side.
        """
        upstream_template = self.factory.makePOTemplate()
        packaging = self.factory.makePackagingLink(
            productseries=upstream_template.productseries, in_ubuntu=True)
        ubuntu_template = self.factory.makePOTemplate(
            distroseries=packaging.distroseries,
            sourcepackagename=packaging.sourcepackagename,
            name=upstream_template.name)
        if side == TranslationSide.UPSTREAM:
            return upstream_template
        else:
            return ubuntu_template

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
        template = self._makePackagingAndTemplates(TranslationSide.UPSTREAM)
        return template

    SHARING_TEXT = """
        This template is sharing translations with .*"""


class TestPOFileSharingInfo(BrowserTestCase, TestSharingInfoMixin):
    """Test display of POFile sharing info."""

    layer = DatabaseFunctionalLayer

    def makeNotSharingObject(self):
        return self.factory.makePOFile()

    NOT_SHARING_TEXT = None

    def makeSharingObject(self):
        template = self._makePackagingAndTemplates(TranslationSide.UPSTREAM)
        # This will also create a copy of pofile in the sharing template.
        pofile = self.factory.makePOFile(
            potemplate=template, create_sharing=True)
        return pofile

    SHARING_TEXT = """
        These translations are shared with .*"""


class TestDummyPOFileSharingInfo(BrowserTestCase, TestSharingInfoMixin):
    """Test display of DummyPOFile sharing info."""

    layer = DatabaseFunctionalLayer

    def makeNotSharingObject(self):
        template = self.factory.makePOTemplate()
        return template.getDummyPOFile(self.factory.makeLanguage())

    NOT_SHARING_TEXT = None

    def makeSharingObject(self):
        template = self._makePackagingAndTemplates(TranslationSide.UPSTREAM)
        # This will also create a copy of pofile in the sharing template.
        return template.getDummyPOFile(self.factory.makeLanguage())

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
        template = self._makePackagingAndTemplates(TranslationSide.UPSTREAM)
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
        template = self._makePackagingAndTemplates(TranslationSide.UBUNTU)
        enable_translations_on_distroseries(template.distroseries)
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
        template = self._makePackagingAndTemplates(TranslationSide.UBUNTU)
        enable_translations_on_distroseries(template.distroseries)
        return template.sourcepackage

    SHARING_TEXT = """
        This source package is sharing translations with .*"""

# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the POTemplate recipe view classes and templates."""

__metaclass__ = type

from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.launchpad.testing.pages import (
    extract_text,
    find_main_content,
    find_tag_by_id,
    )
from lp.app.enums import ServiceUsage
from lp.services.features.testing import FeatureFixture
from lp.testing import BrowserTestCase


def set_translations_usage(obj):
    """Set the translations_usage to LAUNCHPAD."""
    naked_obj = removeSecurityProxy(obj)
    naked_obj.translations_usage = ServiceUsage.LAUNCHPAD


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
        browser = self.getViewBrowser(
            obj, no_login=True, rootsite="translations")
        sharing_info = find_tag_by_id(browser.contents, 'sharing-information')
        self.assertIsNot(None, sharing_info)
        self.assertTextMatchesExpressionIgnoreWhitespace(
            expected_text, extract_text(sharing_info))

    def test_not_sharing(self):
        self._test_sharing_information(
            self.makeNotSharingObject(), self.NOT_SHARING_TEXT)

    def test_sharing(self):
        self._test_sharing_information(
            self.makeSharingObject(), self.SHARING_TEXT)


class TestUpstreamPOTemplateSharingInfo(BrowserTestCase, TestSharingInfoMixin):
    """Test display of template sharing info."""

    layer = DatabaseFunctionalLayer

    def makeNotSharingObject(self):
        return self.factory.makePOTemplate()

    NOT_SHARING_TEXT = """
       This template is not sharing translations with an Ubuntu source package."""
        
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

class TestUpstreamSharingInfo(BrowserTestCase, TestSharingInfoMixin):
    """Test display of product series sharing info."""

    layer = DatabaseFunctionalLayer

    def makeNotSharingObject(self):
        productseries = self.factory.makeProductSeries()
        set_translations_usage(productseries.product)
        return productseries

    NOT_SHARING_TEXT = """
       This project series is not sharing translations with an Ubuntu source package."""

    def makeSharingObject(self):
        productseries = self.factory.makeProductSeries()
        set_translations_usage(productseries.product)
        self.factory.makePackagingLink(
            productseries=productseries, in_ubuntu=True)
        return productseries

    SHARING_TEXT = """
       This project series is sharing translations with .*"""

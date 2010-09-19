# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the product view classes and templates."""

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
import unittest
from mechanize import LinkNotFoundError
import pytz
from zope.component import getUtility

from canonical.launchpad.testing.pages import (
    extract_text,
    find_tag_by_id,
    )
from canonical.launchpad.webapp import canonical_url
from canonical.testing import DatabaseFunctionalLayer
from lp.app.enums import ServiceUsage
from lp.code.enums import BranchType
from lp.code.interfaces.revision import IRevisionSet
from lp.testing import (
    ANONYMOUS,
    BrowserTestCase,
    login,
    login_person,
    TestCaseWithFactory,
    time_counter,
    )
from lp.testing.views import create_initialized_view


class ProductTestBase(TestCaseWithFactory):
    """Common methods for tests herein."""
    layer = DatabaseFunctionalLayer

    def makeProductAndDevelopmentFocusBranch(self, **branch_args):
        """Make a product that has a development focus branch and return both.
        """
        email = self.factory.getUniqueEmailAddress()
        owner = self.factory.makePerson(email=email)
        product = self.factory.makeProduct(owner=owner)
        branch = self.factory.makeProductBranch(
            product=product, **branch_args)
        login(email)
        product.development_focus.branch = branch
        return product, branch


class TestProductCodeIndexView(ProductTestBase):
    """Tests for the product code home page."""


    def getBranchSummaryBrowseLinkForProduct(self, product):
        """Get the 'browse code' link from the product's code home.

        :raises Something: if the branch is not found.
        """
        browser = self.getUserBrowser(canonical_url(product, rootsite='code'))
        return browser.getLink('browse the source code')

    def assertProductBranchSummaryDoesNotHaveBrowseLink(self, product):
        """Assert there is not a browse code link on the product's code home.
        """
        try:
            self.getBranchSummaryBrowseLinkForProduct(product)
        except LinkNotFoundError:
            pass
        else:
            self.fail("Browse link present when it should not have been.")

    def test_browseable_branch_has_link(self):
        # If the product's development focus branch is browseable, there is a
        # 'browse code' link.
        product, branch = self.makeProductAndDevelopmentFocusBranch()
        branch.updateScannedDetails(self.factory.makeRevision(), 1)
        self.assertTrue(branch.code_is_browseable)

        link = self.getBranchSummaryBrowseLinkForProduct(product)
        login(ANONYMOUS)
        self.assertEqual(link.url, branch.browse_source_url)

    def test_unbrowseable_branch_does_not_have_link(self):
        # If the product's development focus branch is not browseable, there
        # is not a 'browse code' link.
        product, branch = self.makeProductAndDevelopmentFocusBranch()
        self.assertFalse(branch.code_is_browseable)

        self.assertProductBranchSummaryDoesNotHaveBrowseLink(product)

    def test_product_code_page_visible_with_private_dev_focus(self):
        # If a user cannot see the product's development focus branch but can
        # see at least one branch for the product they can still see the
        # +code-index page.
        product, branch = self.makeProductAndDevelopmentFocusBranch(
            private=True)
        self.factory.makeProductBranch(product=product)
        # This is just "assertNotRaises"
        self.getUserBrowser(canonical_url(product, rootsite='code'))

    def test_initial_branches_contains_dev_focus_branch(self):
        product, branch = self.makeProductAndDevelopmentFocusBranch()
        view = create_initialized_view(product, '+code-index', rootsite='code')
        self.assertIn(branch, view.initial_branches)

    def test_initial_branches_does_not_contain_private_dev_focus_branch(self):
        product, branch = self.makeProductAndDevelopmentFocusBranch(
            private=True)
        view = create_initialized_view(product, '+code-index', rootsite='code')
        self.assertNotIn(branch, view.initial_branches)

    def test_committer_count_with_revision_authors(self):
        # Test that the code pathing for calling committer_count with
        # valid revision authors is truly tested.
        self.factory.makePerson(email='cthulu@example.com')
        product, branch = self.makeProductAndDevelopmentFocusBranch()
        date_generator = time_counter(
            datetime.now(pytz.UTC) - timedelta(days=30),
            timedelta(days=1))
        self.factory.makeRevisionsForBranch(
            branch, author='cthulu@example.com',
            date_generator=date_generator)
        getUtility(IRevisionSet).updateRevisionCacheForBranch(branch)

        view = create_initialized_view(product, '+code-index', rootsite='code')
        self.assertEqual(view.committer_count, 1)

    def test_committers_count_private_branch(self):
        # Test that calling committer_count will return the proper value
        # for a private branch.
        fsm = self.factory.makePerson(email='flyingpasta@example.com')
        product, branch = self.makeProductAndDevelopmentFocusBranch(
            private=True, owner=fsm)
        date_generator = time_counter(
            datetime.now(pytz.UTC) - timedelta(days=30),
            timedelta(days=1))
        login_person(fsm)
        self.factory.makeRevisionsForBranch(
            branch, author='flyingpasta@example.com',
            date_generator=date_generator)
        getUtility(IRevisionSet).updateRevisionCacheForBranch(branch)

        view = create_initialized_view(product, '+code-index', rootsite='code')
        self.assertEqual(view.committer_count, 1)


class TestProductCodeIndexServiceUsages(ProductTestBase, BrowserTestCase):
    """Tests for the product code page, especially the usage messasges."""

    def test_external_mirrored(self):
        # Test that the correct URL is displayed for a mirrored branch.
        product, branch = self.makeProductAndDevelopmentFocusBranch(
            branch_type=BranchType.MIRRORED,
            url="http://example.com/mybranch")
        self.assertEqual(ServiceUsage.EXTERNAL, product.codehosting_usage)
        browser = self.getUserBrowser(canonical_url(product, rootsite='code'))
        login(ANONYMOUS)
        content = find_tag_by_id(browser.contents, 'external')
        text = extract_text(content)
        expected = ("%(product_title)s hosts its code at %(branch_url)s.  "
                    "Launchpad has a mirror of the master branch "
                    "and you can create branches from it." % dict(
                        product_title=product.title,
                        branch_url=branch.url))
        self.assertTextMatchesExpressionIgnoreWhitespace(expected, text)

    def test_external_remote(self):
        # Test that a remote branch is shown properly.
        product, branch = self.makeProductAndDevelopmentFocusBranch(
            branch_type=BranchType.REMOTE,
            url="http://example.com/mybranch")
        self.assertEqual(ServiceUsage.EXTERNAL,
                         product.codehosting_usage)
        browser = self.getUserBrowser(canonical_url(product, rootsite='code'))
        login(ANONYMOUS)
        content = find_tag_by_id(browser.contents, 'external')
        text = extract_text(content)
        expected = ("%(product_title)s hosts its code at %(branch_url)s.  "
                    "Launchpad does not have a copy of the remote "
                    "branch." % dict(
                        product_title=product.title,
                        branch_url=branch.url))
        self.assertTextMatchesExpressionIgnoreWhitespace(expected, text)

    def test_unknown(self):
        product = self.factory.makeProduct()
        self.assertEqual(ServiceUsage.UNKNOWN, product.codehosting_usage)
        browser = self.getUserBrowser(canonical_url(product, rootsite='code'))
        login(ANONYMOUS)
        content = find_tag_by_id(browser.contents, 'unknown')
        text = extract_text(content)
        expected = (
            "Launchpad does not know where %(product_title)s hosts its code.  "
            "Getting started with code hosting in Launchpad." %
            dict(product_title=product.title))
        self.assertTextMatchesExpressionIgnoreWhitespace(expected, text)

    def test_on_launchpad(self):
        product, branch = self.makeProductAndDevelopmentFocusBranch()
        self.assertEqual(ServiceUsage.LAUNCHPAD, product.codehosting_usage)
        browser = self.getUserBrowser(canonical_url(product, rootsite='code'))
        login(ANONYMOUS)
        text = extract_text(find_tag_by_id(
            browser.contents, 'branch-count-summary'))
        expected = "1 active  branch owned by 1 person"
        preface = text[:len(expected)]
        self.assertTextMatchesExpressionIgnoreWhitespace(expected, preface)

    def test_view_mirror_location(self):
        url = "http://example.com/mybranch"
        product, branch = self.makeProductAndDevelopmentFocusBranch(
            branch_type=BranchType.MIRRORED,
            url=url)
        view = create_initialized_view(product, '+code-index', rootsite='code')
        self.assertEqual(url, view.mirror_location)


class TestProductBranchesViewPortlets(ProductTestBase, BrowserTestCase):
    """Tests for the portlets."""

    def test_is_private(self):
        product, branch = self.makeProductAndDevelopmentFocusBranch(
            private=True)
        self.factory.makeProductBranch(product=product)
        login_person(product.owner)
        browser = self.getUserBrowser(canonical_url(product, rootsite='code'))
        text = extract_text(find_tag_by_id(browser.contents, 'privacy'))
        expected = ("New branches you create for %(name)s are private "
                    "initially." % dict(name=product.name))
        preface = text[:len(expected)]
        self.assertTextMatchesExpressionIgnoreWhitespace(expected, preface)

    def test_is_public(self):
        product, branch = self.makeProductAndDevelopmentFocusBranch(
            private=False)
        self.factory.makeProductBranch(product=product)
        login_person(product.owner)
        browser = self.getUserBrowser(canonical_url(product, rootsite='code'))
        text = extract_text(find_tag_by_id(browser.contents, 'privacy'))
        expected = ("New branches you create for %(name)s are public "
                    "initially." % dict(name=product.title))
        preface = text[:len(expected)]
        self.assertEqual(expected, preface)
        self.assertTextMatchesExpressionIgnoreWhitespace(expected, preface)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

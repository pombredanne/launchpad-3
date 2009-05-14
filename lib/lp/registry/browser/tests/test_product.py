# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the product view classes and templates."""

__metaclass__ = type

from datetime import datetime, timedelta
import unittest

from mechanize import LinkNotFoundError
import pytz

from zope.component import getMultiAdapter

from lp.testing import time_counter, TestCaseWithFactory
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.launchpad.ftests import ANONYMOUS, login
from lp.testing import login_person
from canonical.testing import DatabaseFunctionalLayer


class TestProductCodeIndexView(TestCaseWithFactory):
    """Tests for the product code home page."""

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

    def getBranchSummaryBrowseLinkForProduct(self, product):
        """Get the 'browse code' link from the product's code home.

        :raises Something: if the branch is not found.
        """
        url = canonical_url(product, rootsite='code')
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
        self.assertEqual(
            link.url, branch.codebrowse_url())

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
        url = canonical_url(product, rootsite='code')
        self.factory.makeProductBranch(product=product)
        # This is just "assertNotRaises"
        self.getUserBrowser(canonical_url(product, rootsite='code'))

    def test_initial_branches_contains_dev_focus_branch(self):
        product, branch = self.makeProductAndDevelopmentFocusBranch()
        view = getMultiAdapter(
            (product, LaunchpadTestRequest()), name='+code-index')
        view.initialize()
        self.assertIn(branch, view.initial_branches)

    def test_initial_branches_does_not_contain_private_dev_focus_branch(self):
        product, branch = self.makeProductAndDevelopmentFocusBranch(
            private=True)
        view = getMultiAdapter(
            (product, LaunchpadTestRequest()), name='+code-index')
        view.initialize()
        self.assertNotIn(branch, view.initial_branches)

    def test_committer_count_with_revision_authors(self):
        # Test that the code pathing for calling committer_count with
        # valid revision authors is truly tested.
        cthulu = self.factory.makePerson(email='cthulu@example.com')
        product, branch = self.makeProductAndDevelopmentFocusBranch()
        date_generator = time_counter(
            datetime.now(pytz.UTC) - timedelta(days=30),
            timedelta(days=1))
        self.factory.makeRevisionsForBranch(
            branch, author='cthulu@example.com',
            date_generator=date_generator)

        view = getMultiAdapter(
            (product, LaunchpadTestRequest()), name='+code-index')
        view.initialize()
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

        view = getMultiAdapter(
            (product, LaunchpadTestRequest()), name='+code-index')
        view.initialize()
        self.assertEqual(view.committer_count, 1)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the product view classes and templates."""

__metaclass__ = type

import unittest

from mechanize import LinkNotFoundError

from canonical.config import config
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.ftests import ANONYMOUS, login
from canonical.testing import LaunchpadFunctionalLayer

class TestBrowseDevelopmentFocusCodeLink(TestCaseWithFactory):
    """Tests for the 'browse source' link on the product code home page."""

    layer = LaunchpadFunctionalLayer

    def makeProductAndDevelopmentFocusBranch(self):
        """Make a product that has a development focus branch and return both.
        """
        email = self.factory.getUniqueEmailAddress()
        owner = self.factory.makePerson(email=email)
        product = self.factory.makeProduct(owner=owner)
        branch = self.factory.makeBranch(product=product)
        login(email)
        product.development_focus.user_branch = branch
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
        branch.updateScannedDetails(self.factory.getUniqueString(), 1)
        self.assertTrue(branch.code_is_browseable)

        link = self.getBranchSummaryBrowseLinkForProduct(product)
        login(ANONYMOUS)
        self.assertEqual(
            link.url, config.codehosting.codebrowse_root + branch.unique_name)

    def test_unbrowseable_branch_does_not_have_link(self):
        # If the product's development focus branch is not browseable, there
        # is not a 'browse code' link.
        product, branch = self.makeProductAndDevelopmentFocusBranch()
        self.assertFalse(branch.code_is_browseable)

        self.assertProductBranchSummaryDoesNotHaveBrowseLink(product)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


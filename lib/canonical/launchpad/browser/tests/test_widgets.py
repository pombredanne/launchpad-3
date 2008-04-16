# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for Launchpad-specific widgets."""

__metaclass__ = type

import unittest

from zope.app.tests import ztapi
from zope.interface import implements
from zope.schema import Choice

from canonical.launchpad import _
from canonical.launchpad.browser.widgets import BranchPopupWidget
from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.interfaces import BranchType
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.launchpad.vocabularies import BranchVocabulary
from canonical.testing import LaunchpadFunctionalLayer
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.launchpad.webapp.uri import URI


class DummyLaunchBag:
    """Dummy LaunchBag that we can easily control in our tests."""
    implements(ILaunchBag)

    def __init__(self, user=None, product=None):
        self.user = user
        self.product = product


class TestBranchPopupWidget(unittest.TestCase):

    layer = LaunchpadFunctionalLayer

    def installLaunchBag(self, user=None, product=None):
        bag = DummyLaunchBag(user, product)
        ztapi.provideUtility(ILaunchBag, bag)
        return bag

    def makeBranchPopup(self, context=None):
        if context is None:
            # Pick a random, semi-appropriate context.
            context = self.factory.makeProduct()
        vocab = BranchVocabulary(None)
        return BranchPopupWidget(
            self.makeField(context, vocab), vocab, self.makeRequest())

    def makeField(self, context, vocabulary):
        field = Choice(
            title=_('Branch'), vocabulary=vocabulary, required=False,
            description=_("The Bazaar branch."))
        field.context = context
        return field

    def makeRequest(self):
        return LaunchpadTestRequest()

    def setUp(self):
        login(ANONYMOUS)
        self.factory = LaunchpadObjectFactory()

    def tearDown(self):
        logout()

    def test_getProduct(self):
        """getProduct() returns the product in the LaunchBag."""
        bag = self.installLaunchBag(product=self.factory.makeProduct())
        popup = self.makeBranchPopup()
        self.assertEqual(bag.product, popup.getProduct())

    def test_getPerson(self):
        """getPerson() returns the logged-in user."""
        bag = self.installLaunchBag(user=self.factory.makePerson())
        popup = self.makeBranchPopup()
        self.assertEqual(bag.user, popup.getPerson())

    def test_getBranchNameFromURL(self):
        """getBranchNameFromURL() gets a branch name from a url.

        In general, the name is the last path segment of the URL.
        """
        bag = self.installLaunchBag(product=self.factory.makeProduct())
        popup = self.makeBranchPopup()
        url = self.factory.getUniqueURL()
        name = popup.getBranchNameFromURL(url)
        self.assertEqual(URI(url).path.split('/')[-1], name)

    def test_getBranchNameFromURLWhenAlreadyTaken(self):
        """getBranchNameFromURL() returns a name that isn't already taken."""
        bag = self.installLaunchBag(product=self.factory.makeProduct())
        popup = self.makeBranchPopup()

        # Make sure that the branch name for `url` is already taken.
        url = self.factory.getUniqueURL()
        branch = self.factory.makeBranch(
            product=bag.product, name=popup.getBranchNameFromURL(url))

        # Now that the name is taken for this product, getBranchNameFromURL
        # returns the same name with '-1' at the end.
        self.assertEqual(branch.name + '-1', popup.getBranchNameFromURL(url))

    def test_getBranchNameFromURLWhenAlreadyTakenProgressive(self):
        """getBranchNameFromURL() returns a name that isn't already taken.

        It does this by looping until it finds one that isn't.
        """
        bag = self.installLaunchBag(product=self.factory.makeProduct())
        popup = self.makeBranchPopup()

        # Make sure that the branch name for `url` is already taken.
        url = self.factory.getUniqueURL()
        branch = self.factory.makeBranch(
            product=bag.product, name=popup.getBranchNameFromURL(url))
        self.factory.makeBranch(
            product=bag.product, name=popup.getBranchNameFromURL(url))

        # Now that the name is taken for this product, getBranchNameFromURL
        # returns the same name with '-2' at the end.
        self.assertEqual(branch.name + '-2', popup.getBranchNameFromURL(url))

    def test_makeBranch(self):
        """makeBranch(url) creates a mirrored branch at `url`.

        The owner and registrant are the currently logged-in user, as given by
        getPerson(), and the product is the product in the LaunchBag.
        """
        self.installLaunchBag(
            user=self.factory.makePerson(),
            product=self.factory.makeProduct())
        popup = self.makeBranchPopup()
        url = self.factory.getUniqueURL()
        expected_name = popup.getBranchNameFromURL(url)
        branch = popup.makeBranchFromURL(url)
        self.assertEqual(BranchType.MIRRORED, branch.branch_type)
        self.assertEqual(url, branch.url)
        self.assertEqual(popup.getPerson(), branch.owner)
        self.assertEqual(popup.getPerson(), branch.registrant)
        self.assertEqual(popup.getProduct(), branch.product)
        self.assertEqual(expected_name, branch.name)

# TODO:
# Behaviour when not logged in.
# Behaviour when no product.
# Check that branch is created when the user enters an unknown URL
# Ensure that the branch is mentioned in the notice on the next page.


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

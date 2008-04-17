# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for Launchpad-specific widgets."""

__metaclass__ = type

import unittest

from zope.app.form.interfaces import ConversionError
from zope.app.tests import ztapi
from zope.component import getUtility
from zope.interface import implements
from zope.schema import Choice

from canonical.launchpad import _
from canonical.launchpad.browser.widgets import (
    BranchPopupWidget, NoProductError)
from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.interfaces import BranchType, IBranchSet
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.launchpad.vocabularies import (
    BranchRestrictedOnProductVocabulary, BranchVocabulary)
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

    def assertIs(self, first, second):
        """Assert `first` is `second`."""
        self.assertTrue(first is second, "%r is not %r" % (first, second))

    def installLaunchBag(self, user=None, product=None):
        bag = DummyLaunchBag(user, product)
        ztapi.provideUtility(ILaunchBag, bag)
        return bag

    def makeBranchPopup(self, vocabulary=None):
        # Pick a random, semi-appropriate context.
        context = self.factory.makeProduct()
        if vocabulary is None:
            vocabulary = BranchVocabulary(context)
        request = self.makeRequest()
        return BranchPopupWidget(
            self.makeField(context, vocabulary), vocabulary, request)

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
        self.launch_bag = self.installLaunchBag(
            user=self.factory.makePerson(),
            product=self.factory.makeProduct())
        self.popup = self.makeBranchPopup()

    def tearDown(self):
        logout()

    def test_getProduct(self):
        """getProduct() returns the product in the LaunchBag."""
        self.assertEqual(self.launch_bag.product, self.popup.getProduct())

    def test_getPerson(self):
        """getPerson() returns the logged-in user."""
        self.assertEqual(self.launch_bag.user, self.popup.getPerson())

    def test_getBranchNameFromURL(self):
        """getBranchNameFromURL() gets a branch name from a url.

        In general, the name is the last path segment of the URL.
        """
        url = self.factory.getUniqueURL()
        name = self.popup.getBranchNameFromURL(url)
        self.assertEqual(URI(url).path.split('/')[-1], name)

    def test_getBranchNameFromURLWhenAlreadyTaken(self):
        """getBranchNameFromURL() returns a name that isn't already taken."""
        # Make sure that the branch name for `url` is already taken.
        url = self.factory.getUniqueURL()
        branch = self.factory.makeBranch(
            product=self.launch_bag.product,
            name=self.popup.getBranchNameFromURL(url))

        # Now that the name is taken for this product, getBranchNameFromURL
        # returns the same name with '-1' at the end.
        self.assertEqual(
            branch.name + '-1', self.popup.getBranchNameFromURL(url))

    def test_getBranchNameFromURLWhenAlreadyTakenProgressive(self):
        """getBranchNameFromURL() returns a name that isn't already taken.

        It does this by looping until it finds one that isn't.
        """
        # Make sure that the branch name for `url` is already taken.
        url = self.factory.getUniqueURL()
        branch = self.factory.makeBranch(
            product=self.launch_bag.product,
            name=self.popup.getBranchNameFromURL(url))
        self.factory.makeBranch(
            product=self.launch_bag.product,
            name=self.popup.getBranchNameFromURL(url))

        # Now that the name is taken for this product, getBranchNameFromURL
        # returns the same name with '-2' at the end.
        self.assertEqual(
            branch.name + '-2', self.popup.getBranchNameFromURL(url))

    def test_makeBranch(self):
        """makeBranch(url) creates a mirrored branch at `url`.

        The owner and registrant are the currently logged-in user, as given by
        getPerson(), and the product is the product in the LaunchBag.
        """
        url = self.factory.getUniqueURL()
        expected_name = self.popup.getBranchNameFromURL(url)
        branch = self.popup.makeBranchFromURL(url)
        self.assertEqual(BranchType.MIRRORED, branch.branch_type)
        self.assertEqual(url, branch.url)
        self.assertEqual(self.popup.getPerson(), branch.owner)
        self.assertEqual(self.popup.getPerson(), branch.registrant)
        self.assertEqual(self.popup.getProduct(), branch.product)
        self.assertEqual(expected_name, branch.name)

    def test_makeBranchNoProduct(self):
        """makeBranch(url) returns None if there's no product in LaunchBag.

        Not all contexts for branch registration have products. In particular,
        a bug can be on a source package. When we link a branch to that bug,
        there's no clear product to choose, so we don't choose any.
        """
        self.installLaunchBag(product=None, user=self.factory.makePerson())
        url = self.factory.getUniqueURL()
        self.assertRaises(NoProductError, self.popup.makeBranchFromURL, url)

    def test_makeBranchTrailingSlash(self):
        """makeBranch creates a mirrored branch even if the URL ends with /.
        """
        uri = URI(self.factory.getUniqueURL())
        expected_name = self.popup.getBranchNameFromURL(
            str(uri.ensureNoSlash()))
        branch = self.popup.makeBranchFromURL(str(uri.ensureSlash()))
        self.assertEqual(str(uri.ensureNoSlash()), branch.url)
        self.assertEqual(expected_name, branch.name)

    def test_toFieldValueFallsBackToMakingBranch(self):
        """_toFieldValue falls back to making a branch if it's given a URL."""
        url = self.factory.getUniqueURL()
        # Check that there's no branch with this URL.
        self.assertIs(None, getUtility(IBranchSet).getByUrl(url))

        branch = self.popup._toFieldValue(url)
        self.assertEqual(url, branch.url)

    def test_toFieldValueFetchesTheExistingBranch(self):
        """_toFieldValue returns the existing branch that has that URL."""
        expected_branch = self.factory.makeBranch(BranchType.MIRRORED)
        branch = self.popup._toFieldValue(expected_branch.url)
        self.assertEqual(expected_branch, branch)

    def test_toFieldValueNonURL(self):
        empty_search = 'doesntexist'
        self.assertRaises(
            ConversionError, self.popup._toFieldValue, empty_search)

    def test_toFieldValueNoProduct(self):
        self.installLaunchBag(product=None, user=self.factory.makePerson())
        self.assertRaises(
            ConversionError, self.popup._toFieldValue,
            self.factory.getUniqueURL())

    def test_branchInRestrictedProduct(self):
        # There are two reasons for a URL not being in the vocabulary. One
        # reason is that it's there's no registered branch with that URL. The
        # other is that the vocabulary on this form is restricted to one
        # product, and there *is* a branch with that URL, but it's registered
        # on a different product.

        # Make a popup restricted to a particular product.
        vocab = BranchRestrictedOnProductVocabulary(self.launch_bag.product)
        self.assertEqual(vocab.product, self.launch_bag.product)
        popup = self.makeBranchPopup(vocab)

        # Make a branch on a different product.
        branch = self.factory.makeBranch(BranchType.MIRRORED)
        self.assertNotEqual(self.launch_bag.product, branch.product)

        # Trying to make a branch with that URL will fail.
        self.assertRaises(ConversionError, popup._toFieldValue, branch.url)

    # XXX: JonathanLange 2008-04-17: Not sure how to test what happens when
    # this widget has a good value but other fields have bad values. The
    # correct behavior is to *not* create the branch.

# TODO:
# Ensure that the branch is mentioned in the notice on the next page.


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

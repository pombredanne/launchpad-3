# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Unit tests for Launchpad-specific widgets."""

__metaclass__ = type

import unittest

from zope.schema import Choice

from canonical.launchpad import _
from canonical.launchpad.browser.widgets import BranchPopupWidget
from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.launchpad.vocabularies import BranchVocabulary
from canonical.testing import LaunchpadFunctionalLayer
from canonical.launchpad.webapp.servers import LaunchpadTestRequest


class TestBranchPopupWidget(unittest.TestCase):

    layer = LaunchpadFunctionalLayer

    def makeBranchPopup(self, context):
        vocab = BranchVocabulary(context)
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
        password = self.factory.getUniqueString()
        self.user = self.factory.makePerson(password=password)
        login(self.user.preferredemail.email)

    def tearDown(self):
        logout()

    def test_getProduct(self):
        product = self.factory.makeProduct()
        popup = self.makeBranchPopup(product)
        self.assertEqual(product, popup.getProduct())

    def test_getPerson(self):
        popup = self.makeBranchPopup(self.factory.makeProduct())
        self.assertEqual(self.user, popup.getPerson())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

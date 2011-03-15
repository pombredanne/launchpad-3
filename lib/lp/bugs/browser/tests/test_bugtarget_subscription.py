# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for TestSubscriptionView."""

__metaclass__ = type

from canonical.launchpad.ftests import LaunchpadFormHarness
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.bugs.browser.bugtarget import TargetSubscriptionView
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class TargetSubscriptionViewTestCase(TestCaseWithFactory):
    """Tests for the TargetSubscriptionView."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TargetSubscriptionViewTestCase, self).setUp()
        self.product = self.factory.makeProduct(
            name='widgetsrus', displayname='Widgets R Us')
        self.subscriber = self.factory.makePerson()

    def test_identify_structural_subscriptions(self):
        # This shows simply that we can identify the structural
        # subscriptions for the page.  The content will come later.
        with person_logged_in(self.subscriber):
            sub = self.product.addBugSubscription(
                self.subscriber, self.subscriber)
            harness = LaunchpadFormHarness(
                self.product, TargetSubscriptionView)
            self.assertEqual(
                list(harness.view.structural_subscriptions), [sub])

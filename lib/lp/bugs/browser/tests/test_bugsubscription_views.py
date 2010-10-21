# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for BugSubscription views."""

__metaclass__ = type

from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.services.features.model import FeatureFlag, getFeatureStore
from lp.services.features.testing import FeatureFixture
from lp.testing import TestCaseWithFactory
from lp.testing.views import create_initialized_view


class BugSubscriptionAdvancedFeaturesTestCase(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(BugSubscriptionAdvancedFeaturesTestCase, self).setUp()
        self.useFixture(
            FeatureFixture({
                'malone.advanced-subscriptions.enabled': 'on'}))

    def test_subscribe_uses_bug_notification_level(self):
        # When a user subscribes, their bug notification level is taken
        # into account.
        bug = self.factory.makeBug()
        person = self.factory.makePerson()
        view = create_initialized_view(bug.default_bugtask, '+subscribe')

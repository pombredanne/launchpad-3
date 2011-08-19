# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for BranchSubscriptions."""

__metaclass__ = type

from canonical.launchpad.webapp.interfaces import IPrimaryContext
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class TestBranchSubscriptionPrimaryContext(TestCaseWithFactory):
    # Tests the adaptation of a branch subscription into a primary context.

    layer = DatabaseFunctionalLayer

    def testPrimaryContext(self):
        # The primary context of a branch subscription is the same as the
        # primary context of the branch that the subscription is for.
        subscription = self.factory.makeBranchSubscription()
        self.assertEqual(
            IPrimaryContext(subscription).context,
            IPrimaryContext(subscription.branch).context)

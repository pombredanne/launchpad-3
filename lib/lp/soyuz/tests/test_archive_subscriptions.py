# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Archive features."""

import unittest

from canonical.testing import DatabaseFunctionalLayer

from lp.registry.interfaces.person import PersonVisibility
from lp.testing import login_person, TestCaseWithFactory


class TestArchiveSubscriptions(TestCaseWithFactory):
    """Edge-case tests for private PPA subscribers.

    See also lib/lp/soyuz/stories/ppa/xx-private-ppa-subscription-stories.txt
    """

    layer = DatabaseFunctionalLayer

    def setUp(self):
        """Create a test archive."""
        super(TestArchiveSubscriptions, self).setUp()
        self.private_team = self.factory.makeTeam(
            visibility=PersonVisibility.PRIVATE, name="subscribertest")
        login_person(self.private_team.teamowner)
        self.archive = self.factory.makeArchive(
            private=True, owner=self.private_team)
        self.subscriber = self.factory.makePerson()

    def test_subscriber_can_access_private_team_ppa(self):
        # As per bug 597783, we need to make sure a subscriber can see
        # a private team's PPA after they have been given a subscription.
        self.archive.newSubscription(
            self.subscriber, registrant=self.archive.owner)

        login_person(self.subscriber)
        token = self.archive.newAuthToken(self.subscriber, token=u"mysub")
        url = token.archive_url
        self.assertEqual(token.archive.owner.name, "subscribertest")

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

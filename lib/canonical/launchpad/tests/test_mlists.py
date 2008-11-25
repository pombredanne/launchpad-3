# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test mailing list stuff."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.ftests import login
from canonical.launchpad.interfaces.teammembership import ITeamMembershipSet
from canonical.launchpad.scripts.mlistimport import Importer
from canonical.launchpad.testing.factory import LaunchpadObjectFactory
from canonical.testing.layers import DatabaseFunctionalLayer


factory = LaunchpadObjectFactory()


class TestMailingListImports(unittest.TestCase):
    """Test mailing list imports."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Create a team and a mailing list for the team to test.
        login('foo.bar@canonical.com')
        self.anne = factory.makePersonByName('Anne')
        self.bart = factory.makePersonByName('Bart')
        self.cris = factory.makePersonByName('Cris')
        self.dave = factory.makePersonByName('Dave')
        self.elly = factory.makePersonByName('Elly')
        self.team, self.mailing_list = factory.makeTeamAndMailingList(
            'aardvarks', 'anne')

    def test_simple_import_membership(self):
        # Test the import of a list/team's membership, where all email
        # addresses being imported actually exist in Launchpad.
        importer = Importer('aardvarks')
        importer.importAddresses((
            'anne.person@example.com',
            'bperson@example.org',
            'cris.person@example.com',
            'dperson@example.org',
            'elly.person@example.com',
            ))
        team_memberships = getUtility(ITeamMembershipSet)
        for person in (self.anne, self.bart, self.cris, self.dave, self.elly):
            membership = team_memberships.getByPersonAndTeam(
                person, self.team)
            self.assertTrue(membership is not None,
                            '%s is not a member of %s'
                            % (person.name, self.team.name))
            subscription = self.mailing_list.getSubscription(person)
            self.assertTrue(subscription is not None,
                            '%s is not subscribed to the %s mailing list'
                            % (person.name, self.team.name))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the person vocabularies."""

__metaclass__ = type

from storm.store import Store
from zope.schema.vocabulary import getVocabularyRegistry
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import login_person
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.person import (
    PersonVisibility,
    TeamSubscriptionPolicy,
    )
from lp.testing import TestCaseWithFactory


class VocabularyTestCase(TestCaseWithFactory):

    vocabulary_name = None

    def setUp(self):
        super(VocabularyTestCase, self).setUp()
        self.vocabulary_registry = getVocabularyRegistry()

    def searchVocabulary(self, context, text):
        Store.of(context).flush()
        vocabulary = self.vocabulary_registry.get(
            context, self.vocabulary_name)
        return removeSecurityProxy(vocabulary)._doSearch(text)


class TestValidTeamMemberVocabulary(VocabularyTestCase):
    """Test that the ValidTeamMemberVocabulary behaves as expected."""

    layer = DatabaseFunctionalLayer
    vocabulary_name = 'ValidTeamMember'

    def test_public_team_cannot_be_a_member_of_itself(self):
        # A public team should be filtered by the vocab.extra_clause
        # when provided a search term.
        team = self.factory.makeTeam()
        self.assertNotIn(team, self.searchVocabulary(team, team.name))

    def test_private_team_cannot_be_a_member_of_itself(self):
        # A private team should be filtered by the vocab.extra_clause
        # when provided a search term.
        team = self.factory.makeTeam(
            visibility=PersonVisibility.PRIVATE)
        login_person(team.teamowner)
        self.assertNotIn(team, self.searchVocabulary(team, team.name))

    def test_open_team_cannot_be_a_member_or_a_closed_team(self):
        context_team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.MODERATED)
        open_team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.OPEN)
        moderated_team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.MODERATED)
        restricted_team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.RESTRICTED)
        user = self.factory.makePerson()
        all_possible_members = self.searchVocabulary(context_team, '')
        self.assertNotIn(open_team, all_possible_members)
        self.assertIn(moderated_team, all_possible_members)
        self.assertIn(restricted_team, all_possible_members)
        self.assertIn(user, all_possible_members)

    def test_open_team_can_be_a_member_or_an_open_team(self):
        context_team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.OPEN)
        open_team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.OPEN)
        moderated_team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.MODERATED)
        restricted_team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.RESTRICTED)
        user = self.factory.makePerson()
        all_possible_members = self.searchVocabulary(context_team, '')
        self.assertIn(open_team, all_possible_members)
        self.assertIn(moderated_team, all_possible_members)
        self.assertIn(restricted_team, all_possible_members)
        self.assertIn(user, all_possible_members)

    def test_open_team_vocabulary_displayname(self):
        context_team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.OPEN)
        vocabulary = self.vocabulary_registry.get(
            context_team, self.vocabulary_name)
        self.assertEqual(
            'Select a Person or Team', vocabulary.displayname)

    def test_closed_team_vocabulary_displayname(self):
        context_team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.MODERATED)
        vocabulary = self.vocabulary_registry.get(
            context_team, self.vocabulary_name)
        self.assertEqual(
            'Select a Restricted or Moderated Team or Person',
            vocabulary.displayname)

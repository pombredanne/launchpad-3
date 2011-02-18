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


class VocabularyTestBase:

    vocabulary_name = None

    def setUp(self):
        super(VocabularyTestBase, self).setUp()
        self.vocabulary_registry = getVocabularyRegistry()

    def getVocabulary(self, context):
        return self.vocabulary_registry.get(context, self.vocabulary_name)

    def searchVocabulary(self, context, text):
        Store.of(context).flush()
        vocabulary = self.getVocabulary(context)
        return removeSecurityProxy(vocabulary)._doSearch(text)

    def test_open_team_cannot_be_a_member_of_a_closed_team(self):
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

    def test_open_team_can_be_a_member_of_an_open_team(self):
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

    def test_vocabulary_displayname(self):
        context_team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.OPEN)
        vocabulary = self.getVocabulary(context_team)
        self.assertEqual(
            'Select a Team or Person', vocabulary.displayname)

    def test_open_team_vocabulary_step_title(self):
        context_team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.OPEN)
        vocabulary = self.getVocabulary(context_team)
        self.assertEqual('Search', vocabulary.step_title)

    def test_closed_team_vocabulary_step_title(self):
        context_team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.MODERATED)
        vocabulary = self.getVocabulary(context_team)
        self.assertEqual(
            'Search for a restricted team, a moderated team, or a person',
            vocabulary.step_title)


class TestValidTeamMemberVocabulary(VocabularyTestBase, TestCaseWithFactory):
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


class TestValidTeamOwnerVocabulary(VocabularyTestBase, TestCaseWithFactory):
    """Test that the ValidTeamOwnerVocabulary behaves as expected."""

    layer = DatabaseFunctionalLayer
    vocabulary_name = 'ValidTeamOwner'

    def test_team_cannot_own_itself(self):
        context_team = self.factory.makeTeam()
        results = self.searchVocabulary(context_team, context_team.name)
        self.assertNotIn(context_team, results)

    def test_team_cannot_own_its_owner(self):
        context_team = self.factory.makeTeam()
        owned_team = self.factory.makeTeam(owner=context_team)
        results = self.searchVocabulary(context_team, owned_team.name)
        self.assertNotIn(owned_team, results)

# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the person vocabularies."""

__metaclass__ = type

from storm.store import Store
from zope.schema.vocabulary import getVocabularyRegistry

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
        matches = [
            term.value for term in vocabulary.searchForTerms(text)]
        return matches


class TestValidTeamMemberVocabulary(VocabularyTestCase):
    """Test that the ValidTeamMemberVocabulary behaves as expected."""

    layer = DatabaseFunctionalLayer
    vocabulary_name = 'ValidTeamMember'

    def test_public_team_cannot_be_a_member_of_itself(self):
        # A public team should be filtered by the vocab.extra_clause
        # when provided a search term.
        team = self.factory.makeTeam()
        self.assertFalse(team in self.searchVocabulary(team, team.name))

    def test_private_team_cannot_be_a_member_of_itself(self):
        # A private team should be filtered by the vocab.extra_clause
        # when provided a search term.
        team = self.factory.makeTeam(
            visibility=PersonVisibility.PRIVATE)
        login_person(team.teamowner)
        self.assertFalse(team in self.searchVocabulary(team, team.name))


class TestValidPersonOrClosedTeamVocabulary(TestCaseWithFactory):
    """Test behaviour of ValidPersonOrClosedTeamVocabulary."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestValidPersonOrClosedTeamVocabulary, self).setUp()
        vocabulary_registry = getVocabularyRegistry()
        self.vocabulary = vocabulary_registry.get(
            None, 'ValidPersonOrClosedTeam')

    def searchVocabulary(self, person):
        Store.of(person).flush()
        matches = [
            term.value
            for term in self.vocabulary.searchForTerms(person.name)]
        return person in matches

    def test_contains_no_open_teams(self):
        open_team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.OPEN)
        self.assertFalse(self.searchVocabulary(open_team))

    def test_contains_moderated_teams(self):
        moderated_team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.MODERATED)
        self.assertTrue(self.searchVocabulary(moderated_team))

    def test_contains_restricted_teams(self):
        restricted_team = self.factory.makeTeam(
            subscription_policy=TeamSubscriptionPolicy.RESTRICTED)
        self.assertTrue(self.searchVocabulary(restricted_team))

    def test_contains_users(self):
        user = self.factory.makePerson()
        self.assertTrue(self.searchVocabulary(user))

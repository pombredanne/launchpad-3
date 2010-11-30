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


class TestValidTeamMemberVocabulary(TestCaseWithFactory):
    """Test that the ValidTeamMemberVocabulary behaves as expected."""

    layer = DatabaseFunctionalLayer

    def searchVocabulary(self, team, text):
        vocabulary_registry = getVocabularyRegistry()
        naked_vocabulary = removeSecurityProxy(
            vocabulary_registry.get(team, 'ValidTeamMember'))
        return naked_vocabulary._doSearch(text)

    def test_public_team_cannot_be_a_member_of_itself(self):
        # A public team should be filtered by the vocab.extra_clause
        # when provided a search term.
        team_owner = self.factory.makePerson()
        login_person(team_owner)
        team = self.factory.makeTeam(owner=team_owner)
        Store.of(team).flush()
        self.assertFalse(team in self.searchVocabulary(team, team.name))

    def test_private_team_cannot_be_a_member_of_itself(self):
        # A private team should be filtered by the vocab.extra_clause
        # when provided a search term.
        team_owner = self.factory.makePerson()
        login_person(team_owner)
        team = self.factory.makeTeam(
            owner=team_owner, visibility=PersonVisibility.PRIVATE)
        Store.of(team).flush()
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

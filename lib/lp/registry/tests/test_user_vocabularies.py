# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the user vocabularies."""

__metaclass__ = type

from zope.component import getUtility
from zope.schema.vocabulary import getVocabularyRegistry

from canonical.launchpad.ftests import (
    ANONYMOUS,
    login,
    login_person,
    )
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.registry.interfaces.person import PersonVisibility
from lp.registry.model.person import Person
from lp.testing import TestCaseWithFactory


class TestUserTeamsParticipationPlusSelfVocabulary(TestCaseWithFactory):
    """Test that the UserTeamsParticipationPlusSelf behaves as expected."""

    layer = LaunchpadFunctionalLayer

    def _vocabTermValues(self):
        """Return the token values for the vocab."""
        vocabulary_registry = getVocabularyRegistry()
        vocab = vocabulary_registry.get(
            None, 'UserTeamsParticipationPlusSelf')
        return [term.value for term in vocab]

    def test_user_no_team(self):
        user = self.factory.makePerson()
        login_person(user)
        self.assertEqual([user], self._vocabTermValues())

    def test_user_teams(self):
        # The ordering goes user first, then alphabetical by team display
        # name.
        user = self.factory.makePerson()
        team_owner = self.factory.makePerson()
        login_person(team_owner)
        bravo = self.factory.makeTeam(owner=team_owner, displayname="Bravo")
        bravo.addMember(person=user, reviewer=team_owner)
        alpha = self.factory.makeTeam(owner=team_owner, displayname="Alpha")
        alpha.addMember(person=user, reviewer=team_owner)
        login_person(user)
        self.assertEqual([user, alpha, bravo], self._vocabTermValues())

    def test_user_no_private_teams(self):
        # Private teams are not shown in the vocabulary.
        user = self.factory.makePerson()
        team_owner = self.factory.makePerson()
        login_person(team_owner)
        team = self.factory.makeTeam(owner=team_owner)
        team.addMember(person=user, reviewer=team_owner)
        # Launchpad admin rights are needed to set private.
        login('foo.bar@canonical.com')
        team.visibility = PersonVisibility.PRIVATE
        login_person(user)
        self.assertEqual([user], self._vocabTermValues())

    def test_indirect_team_membership(self):
        # Indirect team membership is shown.
        user = self.factory.makePerson()
        team_owner = self.factory.makePerson()
        login_person(team_owner)
        bravo = self.factory.makeTeam(owner=team_owner, displayname="Bravo")
        bravo.addMember(person=user, reviewer=team_owner)
        alpha = self.factory.makeTeam(owner=team_owner, displayname="Alpha")
        alpha.addMember(
            person=bravo, reviewer=team_owner, force_team_add=True)
        login_person(user)
        self.assertEqual([user, alpha, bravo], self._vocabTermValues())


class TestAllUserTeamsParticipationVocabulary(TestCaseWithFactory):
    """AllUserTeamsParticipation contains all teams joined by a user.

    This includes private teams.
    """

    layer = LaunchpadFunctionalLayer

    def _vocabTermValues(self):
        """Return the token values for the vocab."""
        # XXX Abel Deuring 2010-05-21, bug 583502: We cannot simply iterate
        # over the items of AllUserTeamsPariticipationVocabulary as in
        # class TestUserTeamsParticipationPlusSelfVocabulary.
        # So we iterate over all Person records and return all terms
        # returned by vocabulary.searchForTerms(person.name)
        vocabulary_registry = getVocabularyRegistry()
        vocab = vocabulary_registry.get(None, 'AllUserTeamsParticipation')
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        result = []
        for person in store.find(Person):
            result.extend(
                term.value for term in vocab.searchForTerms(person.name))
        return result

    def test_user_no_team(self):
        user = self.factory.makePerson()
        login_person(user)
        self.assertEqual([], self._vocabTermValues())

    def test_user_is_team_owner(self):
        user = self.factory.makePerson()
        login_person(user)
        team = self.factory.makeTeam(owner=user)
        self.assertEqual([team], self._vocabTermValues())

    def test_user_in_two_teams(self):
        user = self.factory.makePerson()
        login_person(user)
        team1 = self.factory.makeTeam()
        user.join(team1)
        team2 = self.factory.makeTeam()
        user.join(team2)
        self.assertEqual(set([team1, team2]), set(self._vocabTermValues()))

    def test_user_in_private_teams(self):
        # Private teams are included in the vocabulary.
        user = self.factory.makePerson()
        team_owner = self.factory.makePerson()
        login_person(team_owner)
        team = self.factory.makeTeam(owner=team_owner)
        team.addMember(person=user, reviewer=team_owner)
        # Launchpad admin rights are needed to create private teams.
        login('foo.bar@canonical.com')
        team.visibility = PersonVisibility.PRIVATE
        login_person(user)
        self.assertEqual([team], self._vocabTermValues())

    def test_teams_of_anonymous(self):
        # AllUserTeamsPariticipationVocabulary is empty for anoymous users.
        login(ANONYMOUS)
        self.assertEqual([], self._vocabTermValues())

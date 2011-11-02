# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the person vocabularies."""

__metaclass__ = type

from storm.store import Store
from testtools.matchers import Equals
from zope.component import getUtility
from zope.schema.vocabulary import getVocabularyRegistry
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import login_person
from canonical.launchpad.webapp.vocabulary import FilteredVocabularyBase
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.registry.interfaces.irc import IIrcIDSet
from lp.registry.interfaces.person import (
    PersonVisibility,
    TeamSubscriptionPolicy,
    )
from lp.registry.interfaces.karma import IKarmaCacheManager
from lp.registry.vocabularies import ValidPersonOrTeamVocabulary
from lp.testing import (
    StormStatementRecorder,
    TestCaseWithFactory,
    )
from lp.testing.dbuser import dbuser
from lp.testing.matchers import HasQueryCount


class VocabularyTestBase:

    vocabulary_name = None

    def setUp(self):
        super(VocabularyTestBase, self).setUp()
        self.vocabulary_registry = getVocabularyRegistry()

    def getVocabulary(self, context):
        return self.vocabulary_registry.get(context, self.vocabulary_name)

    def searchVocabulary(self, context, text, vocab_filter=None):
        if Store.of(context) is not None:
            Store.of(context).flush()
        vocabulary = self.getVocabulary(context)
        removeSecurityProxy(vocabulary).allow_null_search = True
        return removeSecurityProxy(vocabulary).search(text, vocab_filter)


class TestValidPersonOrTeamVocabulary(VocabularyTestBase,
                                      TestCaseWithFactory):
    """Test that the ValidPersonOrTeamVocabulary behaves as expected.

    Most tests are in lib/lp/registry/doc/vocabularies.txt.
    """

    layer = LaunchpadZopelessLayer
    vocabulary_name = 'ValidPersonOrTeam'

    def test_supported_filters(self):
        # The vocab supports the correct filters.
        self.assertEqual([
            FilteredVocabularyBase.ALL_FILTER,
            ValidPersonOrTeamVocabulary.PERSON_FILTER,
            ValidPersonOrTeamVocabulary.TEAM_FILTER,
            ],
            self.getVocabulary(None).supportedFilters()
        )

    def addKarma(self, person, value, product=None, distribution=None):
        if product:
            kwargs = dict(product_id=product.id)
        elif distribution:
            kwargs = dict(distribution_id=distribution.id)
        with dbuser('karma'):
            getUtility(IKarmaCacheManager).new(
                value, person.id, None, **kwargs)

    def test_people_with_karma_sort_higher(self):
        exact_person = self.factory.makePerson(
            name='fooix', displayname='Fooix Bar')
        prefix_person = self.factory.makePerson(
            name='fooix-bar', displayname='Fooix Bar')
        contributor_person = self.factory.makePerson(
            name='bar', displayname='Fooix Bar')
        product = self.factory.makeProduct()

        # Exact is better than prefix is better than FTI.
        self.assertEqual(
            [exact_person, prefix_person, contributor_person],
            list(self.searchVocabulary(product, u'fooix')))

        # But karma can bump people up, behind the exact match.
        self.addKarma(contributor_person, 500, product=product)
        self.assertEqual(
            [exact_person, contributor_person, prefix_person],
            list(self.searchVocabulary(product, u'fooix')))

        self.addKarma(prefix_person, 500, product=product)
        self.assertEqual(
            [exact_person, prefix_person, contributor_person],
            list(self.searchVocabulary(product, u'fooix')))

    def assertKarmaContextConstraint(self, expected, context):
        """Check that the karma context constraint works.

        Confirms that the karma context constraint matches the expected
        value, and that a search with it works.
        """
        if expected is not None:
            expected = expected % context.id
        self.assertEquals(
            expected,
            removeSecurityProxy(
                self.getVocabulary(context))._karma_context_constraint)
        self.searchVocabulary(context, 'foo')

    def test_product_karma_context(self):
        self.assertKarmaContextConstraint(
            'product = %d', self.factory.makeProduct())

    def test_project_karma_context(self):
        self.assertKarmaContextConstraint(
            'project = %d', self.factory.makeProject())

    def test_distribution_karma_context(self):
        self.assertKarmaContextConstraint(
            'distribution = %d', self.factory.makeDistribution())

    def test_root_karma_context(self):
        self.assertKarmaContextConstraint(None, None)

    def test_irc_nick_match_is_not_case_sensitive(self):
        person = self.factory.makePerson()
        irc = getUtility(IIrcIDSet).new(
            person, 'somenet', 'MiXeD' + self.factory.getUniqueString())
        self.assertContentEqual(
            [person], self.searchVocabulary(person, irc.nickname.lower()))

    def _person_filter_tests(self, person):
        results = self.searchVocabulary(None, '', 'PERSON')
        for personorteam in results:
            self.assertFalse(personorteam.is_team)
        results = self.searchVocabulary(None, u'fred', 'PERSON')
        self.assertEqual([person], list(results))

    def test_person_filter(self):
        # Test that the person filter only returns people.
        person = self.factory.makePerson(
            name="fredperson", email="fredperson@foo.com")
        self.factory.makeTeam(
            name="fredteam", email="fredteam@foo.com")
        self._person_filter_tests(person)

    def _team_filter_tests(self, team):
        results = self.searchVocabulary(None, '', 'TEAM')
        for personorteam in results:
            self.assertTrue(personorteam.is_team)
        results = self.searchVocabulary(None, u'fred', 'TEAM')
        self.assertEqual([team], list(results))

    def test_team_filter(self):
        # Test that the team filter only returns teams.
        self.factory.makePerson(
            name="fredperson", email="fredperson@foo.com")
        team = self.factory.makeTeam(
            name="fredteam", email="fredteam@foo.com")
        self._team_filter_tests(team)
        self._team_filter_tests(team)


class TestValidPersonOrTeamPreloading(VocabularyTestBase,
                                      TestCaseWithFactory):
    """Tests for ValidPersonOrTeamVocabulary's preloading behaviour."""

    layer = DatabaseFunctionalLayer
    vocabulary_name = 'ValidPersonOrTeam'

    def test_preloads_irc_nicks_and_preferredemail(self):
        """Test that IRC nicks and preferred email addresses are preloaded."""
        # Create three people with IRC nicks, and one without.
        people = []
        for num in range(3):
            person = self.factory.makePerson(displayname='foobar %d' % num)
            getUtility(IIrcIDSet).new(person, 'launchpad', person.name)
            people.append(person)
        people.append(self.factory.makePerson(displayname='foobar 4'))

        # Remember the current values for checking later, and throw out
        # the cache.
        expected_nicks = dict(
            (person.id, list(person.ircnicknames)) for person in people)
        expected_emails = dict(
            (person.id, person.preferredemail) for person in people)
        Store.of(people[0]).invalidate()

        results = list(self.searchVocabulary(None, u'foobar'))
        with StormStatementRecorder() as recorder:
            self.assertEquals(4, len(results))
            for person in results:
                self.assertEqual(
                    expected_nicks[person.id], person.ircnicknames)
                self.assertEqual(
                    expected_emails[person.id], person.preferredemail)
        self.assertThat(recorder, HasQueryCount(Equals(0)))


class TeamMemberVocabularyTestBase(VocabularyTestBase):

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


class TestValidTeamMemberVocabulary(TeamMemberVocabularyTestBase,
                                    TestCaseWithFactory):
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


class TestValidTeamOwnerVocabulary(TeamMemberVocabularyTestBase,
                                   TestCaseWithFactory):
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


class TestValidPersonVocabulary(VocabularyTestBase,
                                      TestCaseWithFactory):
    """Test that the ValidPersonVocabulary behaves as expected."""

    layer = LaunchpadZopelessLayer
    vocabulary_name = 'ValidPerson'

    def test_supported_filters(self):
        # The vocab shouldn't support person or team filters.
        self.assertEqual([], self.getVocabulary(None).supportedFilters())


class TestValidTeamVocabulary(VocabularyTestBase,
                                      TestCaseWithFactory):
    """Test that the ValidTeamVocabulary behaves as expected."""

    layer = LaunchpadZopelessLayer
    vocabulary_name = 'ValidTeam'

    def test_supported_filters(self):
        # The vocab shouldn't support person or team filters.
        self.assertEqual([], self.getVocabulary(None).supportedFilters())

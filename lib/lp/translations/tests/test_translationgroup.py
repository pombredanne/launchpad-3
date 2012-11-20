# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for `TranslationGroup` and related classes."""

__metaclass__ = type

from lazr.restfulclient.errors import Unauthorized
import transaction
from zope.component import getUtility

from lp.app.enums import InformationType
from lp.registry.interfaces.teammembership import (
    ITeamMembershipSet,
    TeamMembershipStatus,
    )
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    WebServiceTestCase,
    )
from lp.testing.layers import ZopelessDatabaseLayer
from lp.translations.interfaces.translationgroup import ITranslationGroupSet


class TestTranslationGroup(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def _setup_products(self):
        """Helper to setup one public one non-public product."""
        user = self.factory.makePerson()
        private_owner = self.factory.makePerson()
        group = self.factory.makeTranslationGroup()

        with person_logged_in(user):
            public_product = self.factory.makeProduct()
            public_product.translationgroup = group

        with person_logged_in(private_owner):
            private_product = self.factory.makeProduct(
                information_type=InformationType.PROPRIETARY,
                owner=private_owner)
            private_product.translationgroup = group

        return user, private_owner

    def test_non_public_products_hidden(self):
        """Non Public products are not returned via products attribute."""
        public_user, private_user = self._setup_products()

        with person_logged_in(public_user):
            self.assertEqual(
                1,
                group.products.count(),
                'There is only one public product for this user')

        with person_logged_in(private_user):
            self.assertEqual(
                2,
                group.products.count(),
                'There are two for the private user.')

    def test_non_public_products_hidden_for_display(self):
        """Non Public products are not returned via fetchProjectsForDisplay."""
        public_user, private_user = self._setup_products()

        # Magical transaction so our data shows up via ISlaveStore
        import transaction
        transaction.commit()

        with person_logged_in(public_user):
            self.assertEqual(
                1,
                len(group.fetchProjectsForDisplay()),
                'There is only one public product for the public user')

        with person_logged_in(private_user):
            self.assertEqual(
                2,
                len(group.fetchProjectsForDisplay()),
                'Both products show for the private user.')


class TestTranslationGroupSet(TestCaseWithFactory):
    layer = ZopelessDatabaseLayer

    def _enrollInTeam(self, team, member):
        """Make `member` a member of `team`."""
        getUtility(ITeamMembershipSet).new(
            member, team, TeamMembershipStatus.APPROVED, team.teamowner)

    def _makeTranslationTeam(self, group, member, language_code):
        """Create translation team and enroll `member` in it."""
        team = self.factory.makeTeam()
        self.factory.makeTranslator(language_code, group=group, person=team)
        self._enrollInTeam(team, member)
        return team

    def test_getByPerson_distinct_membership(self):
        # A person can be in a translation team multiple times through
        # indirect membership, but a group using that team will show up
        # only once in getByPerson.
        group = self.factory.makeTranslationGroup()
        person = self.factory.makePerson()
        translation_team = self._makeTranslationTeam(group, person, 'nl')

        nested_team = self.factory.makeTeam()
        self._enrollInTeam(translation_team, nested_team)
        self._enrollInTeam(nested_team, person)

        self.assertEqual(
            [group],
            list(getUtility(ITranslationGroupSet).getByPerson(person)))

    def test_getByPerson_distinct_translationteam(self):
        # getByPerson returns a group only once even if the person is a
        # member of multiple translation teams in the group.
        group = self.factory.makeTranslationGroup()
        person = self.factory.makePerson()

        self._makeTranslationTeam(group, person, 'es')
        self._makeTranslationTeam(group, person, 'ca')

        self.assertEqual(
            [group],
            list(getUtility(ITranslationGroupSet).getByPerson(person)))


class TestWebService(WebServiceTestCase):
    layer = ZopelessDatabaseLayer

    def test_getByName(self):
        """getByName returns the TranslationGroup for the specified name."""
        group = self.factory.makeTranslationGroup()
        transaction.commit()
        ws_group = self.service.translation_groups.getByName(name=group.name)
        self.assertEqual(group.name, ws_group.name)

    def test_attrs(self):
        """TranslationGroup provides the expected attributes."""
        group = self.factory.makeTranslationGroup()
        transaction.commit()
        ws_group = self.wsObject(group)
        self.assertEqual(group.name, ws_group.name)
        self.assertEqual(group.title, ws_group.title)
        ws_group.name = 'foo'
        e = self.assertRaises(Unauthorized, ws_group.lp_save)
        self.assertIn("'name', 'launchpad.Edit'", str(e))

    def test_list_groups(self):
        """Listing translation groups works and is accurate."""
        translation_group_set = getUtility(ITranslationGroupSet)
        self.assertContentEqual(
            [group.name for group in translation_group_set],
            [group.name for group in self.service.translation_groups])

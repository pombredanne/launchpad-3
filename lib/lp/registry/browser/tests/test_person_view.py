# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.webapp.interfaces import NotFoundError
from lp.registry.interfaces.karma import IKarmaCacheManager
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import LaunchpadZopelessLayer
from lp.registry.browser.person import PersonView
from lp.registry.model.karma import KarmaCategory
from lp.testing import TestCaseWithFactory
from lp.testing.views import create_initialized_view


class TestPersonViewKarma(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        person = self.factory.makePerson()
        product = self.factory.makeProduct()
        self.view = PersonView(
            person, LaunchpadTestRequest())
        self._makeKarmaCache(
            person, product, KarmaCategory.byName('bugs'))
        self._makeKarmaCache(
            person, product, KarmaCategory.byName('answers'))
        self._makeKarmaCache(
            person, product, KarmaCategory.byName('code'))

    def test_karma_category_sort(self):
        categories = self.view.contributed_categories
        category_names = []
        for category in categories:
            category_names.append(category.name)

        self.assertEqual(category_names, [u'code', u'bugs', u'answers'],
                         'Categories are not sorted correctly')

    def _makeKarmaCache(self, person, product, category, value=10):
        """ Create and return a KarmaCache entry with the given arguments.

        In order to create the KarmaCache record we must switch to the DB
        user 'karma', so tests that need a different user after calling
        this method should do run switchDbUser() themselves.
        """

        LaunchpadZopelessLayer.switchDbUser('karma')

        cache_manager = getUtility(IKarmaCacheManager)
        karmacache = cache_manager.new(
            value, person.id, category.id, product_id=product.id)

        try:
            cache_manager.updateKarmaValue(
                value, person.id, category_id=None, product_id=product.id)
        except NotFoundError:
            cache_manager.new(
                value, person.id, category_id=None, product_id=product.id)

        # We must commit here so that the change is seen in other transactions
        # (e.g. when the callsite issues a switchDbUser() after we return).
        LaunchpadZopelessLayer.commit()
        return karmacache


class TestShouldShowPpaSection(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.person = self.factory.makePerson(name='mowgli')
        self.person_ppa = self.factory.makeArchive(owner=self.person)
        self.team = self.factory.makeTeam(name='jbook')
        self.team_ppa = self.factory.makeArchive(owner=self.team)
        self.person_view = create_initialized_view(self.person, name='+index')
        self.team_view = create_initialized_view(self.team, name='+index')

    def test_for_user_with_view_permission(self):
        # Show PPA section if context has at least one PPA the user is
        # authorised to view.
        login(ANONYMOUS)
        self.failUnless(self.person_view.should_show_ppa_section)
        self.person_ppa.private = True
        self.person_ppa.buildd_secret = "secret"
        self.failIf(self.person_view.should_show_ppa_section)

    def test_for_user_with_view_permission_and_no_ppas(self):
        # Do not show PPA section if context has no PPAs the user is
        # authorised to view.
        pass

    def test_for_user_with_edit_permission(self):
        # Show PPA section if user has edit permission for context.
        pass

    def test_for_user_without_edit_permission_and_no_ppas(self):
        # Do not show the PPA section if there are no PPAs and if the user has
        # no edit permission for context.
        pass


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

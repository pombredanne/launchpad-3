# Copyright 2012 Canonical Ltd. This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test views that manage sharing."""

__metaclass__ = type

import simplejson

from BeautifulSoup import BeautifulSoup
from lazr.restful.interfaces import IJSONRequestCache
from zope.component import getUtility
from zope.security.interfaces import Unauthorized

from lp.app.interfaces.services import IService
from lp.services.features.testing import FeatureFixture
from lp.services.webapp.publisher import canonical_url
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.pages import setupBrowserForUser
from lp.testing.views import (
    create_initialized_view,
    create_view,
    )


ENABLED_FLAG = {'disclosure.enhanced_sharing.enabled': 'true'}
WRITE_FLAG = {'disclosure.enhanced_sharing.writable': 'true'}


class PillarSharingViewTestMixin:
    """Test the PillarSharingView."""

    layer = DatabaseFunctionalLayer

    def test_init_without_feature_flag(self):
        # We need a feature flag to enable the view.
        self.assertRaises(
            Unauthorized, create_initialized_view, self.pillar, '+sharing')

    def test_init_with_feature_flag(self):
        # The view works with a feature flag.
        with FeatureFixture(ENABLED_FLAG):
            view = create_initialized_view(self.pillar, '+sharing')
            self.assertEqual('Sharing', view.page_title)

    def test_sharing_menu_without_feature_flag(self):
        url = canonical_url(self.pillar)
        browser = setupBrowserForUser(user=self.driver)
        browser.open(url)
        soup = BeautifulSoup(browser.contents)
        sharing_menu = soup.find('a', {'class': 'menu-link-sharing'})
        self.assertIsNone(sharing_menu)

    def test_sharing_menu_with_feature_flag(self):
        with FeatureFixture(ENABLED_FLAG):
            url = canonical_url(self.pillar)
            browser = setupBrowserForUser(user=self.driver)
            browser.open(url)
            soup = BeautifulSoup(browser.contents)
            sharing_url = canonical_url(self.pillar, view_name='+sharing')
            sharing_menu = soup.find('a', {'href': sharing_url})
            self.assertIsNotNone(sharing_menu)

    def test_picker_config(self):
        # Test the config passed to the disclosure sharing picker.
        with FeatureFixture(ENABLED_FLAG):
            view = create_view(self.pillar, name='+sharing')
            picker_config = simplejson.loads(view.json_sharing_picker_config)
            self.assertTrue('vocabulary_filters' in picker_config)
            self.assertEqual(
                'Share with a user or team',
                picker_config['header'])
            self.assertEqual(
                'ValidPillarOwner', picker_config['vocabulary'])

    def test_view_data_model(self):
        # Test that the json request cache contains the view data model.
        with FeatureFixture(ENABLED_FLAG):
            view = create_initialized_view(self.pillar, name='+sharing')
            cache = IJSONRequestCache(view.request)
            self.assertIsNotNone(cache.objects.get('information_types'))
            self.assertIsNotNone(cache.objects.get('sharing_permissions'))
            aps = getUtility(IService, 'sharing')
            observers = aps.getPillarSharees(self.pillar)
            self.assertEqual(observers, cache.objects.get('sharee_data'))

    def test_view_write_enabled_without_feature_flag(self):
        # Test that sharing_write_enabled is not set without the feature flag.
        with FeatureFixture(ENABLED_FLAG):
            login_person(self.owner)
            view = create_initialized_view(self.pillar, name='+sharing')
            cache = IJSONRequestCache(view.request)
            self.assertFalse(cache.objects.get('sharing_write_enabled'))

    def test_view_write_enabled_with_feature_flag(self):
        # Test that sharing_write_enabled is set when required.
        with FeatureFixture(WRITE_FLAG):
            view = create_initialized_view(self.pillar, name='+sharing')
            cache = IJSONRequestCache(view.request)
            self.assertFalse(cache.objects.get('sharing_write_enabled'))
            login_person(self.owner)
            view = create_initialized_view(self.pillar, name='+sharing')
            cache = IJSONRequestCache(view.request)
            self.assertTrue(cache.objects.get('sharing_write_enabled'))


class TestProductSharingView(PillarSharingViewTestMixin,
                                 TestCaseWithFactory):
    """Test the PillarSharingView with products."""

    def setUp(self):
        super(TestProductSharingView, self).setUp()
        self.driver = self.factory.makePerson()
        self.owner = self.factory.makePerson()
        self.pillar = self.factory.makeProduct(
            owner=self.owner, driver=self.driver)
        login_person(self.driver)


class TestDistributionSharingView(PillarSharingViewTestMixin,
                                      TestCaseWithFactory):
    """Test the PillarSharingView with distributions."""

    def setUp(self):
        super(TestDistributionSharingView, self).setUp()
        self.driver = self.factory.makePerson()
        self.owner = self.factory.makePerson()
        self.pillar = self.factory.makeDistribution(
            owner=self.owner, driver=self.driver)
        login_person(self.driver)

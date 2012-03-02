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
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.views import (
    create_initialized_view,
    create_view,
    )


FLAG = {'disclosure.enhanced_sharing.enabled': 'true'}


class TestProductSharingView(TestCaseWithFactory):
    """Test the ProductSharingView."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProductSharingView, self).setUp()
        driver = self.factory.makePerson()
        self.product = self.factory.makeProduct(driver=driver)
        login_person(driver)

    def test_init_without_feature_flag(self):
        # We need a feature flag to enable the view.
        self.assertRaises(
            Unauthorized, create_initialized_view, self.product, '+sharing')

    def test_init_with_feature_flag(self):
        # The view works with a feature flag.
        with FeatureFixture(FLAG):
            view = create_initialized_view(self.product, '+sharing')
            self.assertEqual('Sharing', view.page_title)

    def sharing_menu(self):
        with FeatureFixture(FLAG):
            view = create_initialized_view(self.product, '+sharing')
            soup = BeautifulSoup(view())
            sharing_menu = soup.find('a', {'class': 'menu-link-sharing'})
            self.assertIsNone(sharing_menu)

    def test_picker_config(self):
        # Test the config passed to the disclosure sharing picker.
        with FeatureFixture(FLAG):
            view = create_view(self.product, name='+sharing')
            picker_config = simplejson.loads(view.json_sharing_picker_config)
            self.assertTrue('vocabulary_filters' in picker_config)
            self.assertEqual(
                'Grant access to %s' % self.product.displayname,
                picker_config['header'])
            self.assertEqual(
                'ValidPillarOwner', picker_config['vocabulary'])

    def test_view_data_model(self):
        # Test that the json request cache contains the view data model.
        with FeatureFixture(FLAG):
            view = create_initialized_view(self.product, name='+sharing')
            cache = IJSONRequestCache(view.request)
            self.assertIsNotNone(cache.objects.get('access_policies'))
            self.assertIsNotNone(cache.objects.get('sharing_permissions'))
            aps = getUtility(IService, 'accesspolicy')
            observers = aps.getPillarObservers(self.product)
            self.assertEqual(observers, cache.objects.get('observer_data'))

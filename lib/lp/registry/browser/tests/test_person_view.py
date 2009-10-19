# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import NotFoundError
from lp.registry.interfaces.karma import IKarmaCacheManager
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import LaunchpadZopelessLayer
from lp.registry.browser.person import PersonView
from lp.registry.model.karma import KarmaCategory
from lp.testing import TestCaseWithFactory


class TestPersonView(TestCaseWithFactory):

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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

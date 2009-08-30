# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from canonical.config import config
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import LaunchpadZopelessLayer
from canonical.database.sqlbase import cursor, sqlvalues
from lp.registry.browser.person import PersonView
from lp.testing import TestCaseWithFactory
from zope.component import getUtility
from canonical.launchpad.interfaces import IKarmaCacheManager, NotFoundError
from lp.registry.model.karma import KarmaCategory

class TestPersonView(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.person = self.factory.makePerson()
        self.view = PersonView(self.person,
                               LaunchpadTestRequest())
        self.makeKarmaCache(person=self.person, 
            category=KarmaCategory.byName('bugs'))
        self.makeKarmaCache(person=self.person, 
            category=KarmaCategory.byName('answers'))
        self.makeKarmaCache(person=self.person, 
            category=KarmaCategory.byName('code')) 

    def test_karma_category_sort(self):
        categories = self.view.contributed_categories
        category_names = []
        for category in categories:
            category_names.append(category.name)

        self.assertEqual(category_names, [u'code', u'bugs', u'answers'], 
                         'Categories are not sorted correctly')

    def makeKarmaCache(self, person, category, value=10, product=None):
        if product is None:
            product = self.factory.makeProduct()

        # karmacacheupdater is the only db user who has write access to
        # the KarmaCache table so we switch to it here
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

        LaunchpadZopelessLayer.commit()
        LaunchpadZopelessLayer.switchDbUser('launchpad')

        return karmacache

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

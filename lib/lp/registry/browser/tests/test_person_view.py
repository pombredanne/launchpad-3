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
from canonical.launchpad.interfaces import IKarmaCacheManager

class TestPerson(TestCaseWithFactory):
    """Test Person view."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        # Create a person
        TestCaseWithFactory.setUp(self)
        self.person = self.factory.makePerson()
        self.view = PersonView(self.person,
                               LaunchpadTestRequest())

    def test_karma_category_sort(self):
        # Add karma to some categories for the user
        self.makeKarmaCache(person=self.person, category_id=2)
        self.makeKarmaCache(person=self.person, category_id=7)
        self.makeKarmaCache(person=self.person, category_id=8) 

        # Get contributed categories for the factory user 
        categories = self.view.contributed_categories
        category_names = []
        for category in categories:
            category_names.append(category.name)

        # Assert that the contributed categories are sorted correctly
        self.assertEqual(category_names, [u'code', u'bugs', u'answers'], 
                         'Categories are not sorted correctly')

    def makeKarmaCache(self, person=None, value=10, category_id=2,
                       product_id=5):
        # Create KarmaCache Record
        LaunchpadZopelessLayer.switchDbUser(config.karmacacheupdater.dbuser)
        karmacache = getUtility(IKarmaCacheManager).new(
            person_id=person.id, value=value, category_id=category_id,
            product_id=product_id)
        LaunchpadZopelessLayer.commit()

        # Update totals for this product
        query = """
            INSERT INTO KarmaCache 
                (person, category, karmavalue, product, distribution,
                 sourcepackagename, project)
            SELECT person, NULL, SUM(karmavalue), product, NULL, NULL, NULL
            FROM KarmaCache
            WHERE product = %(product)s
               AND person = %(person)s 
            GROUP BY person, product
            """ % sqlvalues(person=person.id, product=product_id)
        cur = cursor()
        cur.execute(query)

        return karmacache

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

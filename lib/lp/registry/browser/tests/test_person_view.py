# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from canonical.config import config
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import LaunchpadZopelessLayer
from canonical.database.sqlbase import cursor
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
        cur = cursor()
        karmacache = self.makeKarmaCache(person=self.person, category_id=2)
        karmacache = self.makeKarmaCache(person=self.person, category_id=7)
        karmacache = self.makeKarmaCache(person=self.person, category_id=8) 

        # Update Karma totals
        self.updateKarmaTotals()

        # Get contributed categories for the user
        categories = self.view.contributed_categories
        category_names = []
        for category in categories:
            category_names.append(category.name)

        self.assertEqual(category_names, [u'code', u'bugs', u'answers'], 
                         'Categories are not sorted correctly')

    def makeKarmaCache(self, person=None, value=10, category_id=2,
                       product_id=5):

        LaunchpadZopelessLayer.switchDbUser(config.karmacacheupdater.dbuser)
        karmacache = getUtility(IKarmaCacheManager).new(
            person_id=person.id, value=value, category_id=category_id,
            product_id=product_id)
        LaunchpadZopelessLayer.commit()

        return karmacache

    def updateKarmaTotals(self):
        LaunchpadZopelessLayer.switchDbUser(config.karmacacheupdater.dbuser)

        cur = cursor()
        cur.execute("DELETE FROM KarmaCache WHERE category IS NULL")
        cur.execute("""
            DELETE FROM KarmaCache
            WHERE project IS NOT NULL AND product IS NULL""")
        cur.execute("""
            DELETE FROM KarmaCache
            WHERE category IS NOT NULL AND project IS NULL AND product IS NULL
                  AND distribution IS NULL AND sourcepackagename IS NULL""")
        cur.execute("DELETE FROM KarmaCache WHERE karmavalue <= 0")

        # - All actions with a specific category of a person.
        cur.execute("""
            INSERT INTO KarmaCache 
                (person, category, karmavalue, product, distribution,
                 sourcepackagename, project)
            SELECT person, category, SUM(karmavalue), NULL, NULL, NULL, NULL
            FROM KarmaCache
            WHERE category IS NOT NULL
            GROUP BY person, category
            """)

        # - All actions of a person on a given product.
        cur.execute("""
            INSERT INTO KarmaCache 
                (person, category, karmavalue, product, distribution,
                 sourcepackagename, project)
            SELECT person, NULL, SUM(karmavalue), product, NULL, NULL, NULL
            FROM KarmaCache
            WHERE product IS NOT NULL
            GROUP BY person, product
            """)

        # - All actions of a person on a given distribution.
        cur.execute("""
            INSERT INTO KarmaCache 
                (person, category, karmavalue, product, distribution,
                 sourcepackagename, project)
            SELECT person, NULL, SUM(karmavalue), NULL, distribution, NULL, NULL
            FROM KarmaCache
            WHERE distribution IS NOT NULL
            GROUP BY person, distribution
            """)

        # - All actions of a person on a given project.
        cur.execute("""
            INSERT INTO KarmaCache 
                (person, category, karmavalue, product, distribution,
                 sourcepackagename, project)
            SELECT person, NULL, SUM(karmavalue), NULL, NULL, NULL,
                   Product.project
            FROM KarmaCache
            JOIN Product ON product = Product.id
            WHERE Product.project IS NOT NULL AND product IS NOT NULL
                  AND category IS NOT NULL
            GROUP BY person, Product.project
            """)

        # - All actions with a specific category of a person on a given project
        # IMPORTANT: This has to be the latest step; otherwise the rows
        # inserted here will be included in the calculation of the overall
        # karma of a person on a given project.
        cur.execute("""
            INSERT INTO KarmaCache 
                (person, category, karmavalue, product, distribution,
                 sourcepackagename, project)
            SELECT person, category, SUM(karmavalue), NULL, NULL, NULL,
                   Product.project
            FROM KarmaCache
            JOIN Product ON product = Product.id
            WHERE Product.project IS NOT NULL AND product IS NOT NULL
                  AND category IS NOT NULL
            GROUP BY person, category, Product.project
            """)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

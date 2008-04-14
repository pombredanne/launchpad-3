"""
Tests to make sure that SQLOS works as expected in our environment.
"""
import unittest
from threading import Thread

import sqlos
import sqlobject
import transaction
from zope.rdb.interfaces import DatabaseException

from canonical.testing import LaunchpadFunctionalLayer

class Beer(sqlos.SQLOS):
    _columns = [
        sqlobject.StringCol('name', unique=True, notNull=True),
        sqlobject.IntCol('rating', default=None),
        ]

class TestSQLOS(unittest.TestCase):
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestSQLOS, self).setUp()
        Beer.createTable()
        transaction.commit()

    def tearDown(self):
        transaction.abort()
        super(TestSQLOS, self).tearDown()

    def test_multipleTransations(self):
        # Here we create a Beer and make modifications in a number
        # of different transactions
        transaction.begin()
        b = Beer(name='Victoria Bitter')
        id = b.id
        transaction.commit()
        transaction.begin()
        b = Beer.get(id)
        self.failUnlessEqual(b.name, 'Victoria Bitter')
        b.rating = 4
        transaction.commit()
        transaction.begin()
        b = Beer.get(id)
        self.failUnlessEqual(b.rating, 4)
        b.rating = 5
        transaction.commit()
        transaction.begin()
        b = Beer.get(id)
        self.failUnlessEqual(b.rating, 5)
        transaction.commit()

    def test_threads(self):
        # Here we create a number of Beers in seperate threads
        def doit():
            transaction.begin()
            b = Beer(name=beer_name)
            b.rating = beer_rating
            transaction.commit()

        beer_name = 'Victoria Bitter'
        beer_rating = 4
        t = Thread(target=doit)
        t.start()
        t.join()

        beer_name = 'Singa'
        beer_rating = 6
        t = Thread(target=doit)
        t.start()
        t.join()

        # And make sure they are both seen
        transaction.begin()
        beers = list(Beer.select())
        self.failUnlessEqual(len(beers), 2)
        transaction.commit()

    def test_exception(self):

        # We have observed if a database transaction ends badly, it is
        # not reset for future Zope transactions. To test this, we cause
        # a database exception
        transaction.begin()
        Beer(name='Victoria Bitter')
        try:
            Beer(name='Victoria Bitter')
            self.fail('Unique constraint was not triggered')
        except DatabaseException:
            pass
        transaction.abort()

        # Now start a new transaction and see if we can do anything
        transaction.begin()
        Beer(name='Singa')
        transaction.commit()

    def test_percent(self):
        # A psycopg bug was being triggered by Zope3, where queries with
        # a single % were raising exceptions
        b = Beer(name='100%', rating=2)
        id = b.id

        b = Beer.get(id)
        Beer.selectBy(name='100%')

def test_suite():
    # Tests disabled - no gain
    suite = unittest.TestSuite()
    #suite.addTest(unittest.makeSuite(TestSQLOS))
    return suite

if __name__ == '__main__':
    unittest.main()


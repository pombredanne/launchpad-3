"""
Tests to make sure that initZopeless works as expected.
"""
import unittest, warnings, sys, psycopg
from canonical.lp import initZopeless
from canonical.database.sqlbase import SQLBase, alreadyInstalledMsg
from canonical.ftests.pgsql import PgTestCase
from threading import Thread

from sqlobject import StringCol, IntCol


class MoreBeer(SQLBase):
    '''Simple SQLObject class used for testing'''
    # test_sqlos defines a Beer SQLObject already, so we call this one MoreBeer
    # to avoid confusing SQLObject.
    _columns = [
        StringCol('name', unique=True, notNull=True),
        IntCol('rating', default=None),
        ]


class TestInitZopeless(PgTestCase):
    dbname = 'ftest_tmp'
    
    def test_initZopelessTwice(self):
        # Hook the warnings module, so we can verify that we get the expected
        # warning.
        showwarning = warnings.showwarning
        warnings.showwarning = self.expectedWarning
        self.warned = False
        try:
            # Calling initZopeless with the same arguments twice should return
            # the exact same object twice, but also emit a warning.
            tm1 = initZopeless(dbname=self.dbname, dbhost='')
            tm2 = initZopeless(dbname=self.dbname, dbhost='')
        finally:
            # Put the warnings module back the way we found it.
            warnings.showwarning = showwarning
        self.failUnless(tm1 is tm2)
        self.failUnless(self.warned)
            
    def expectedWarning(self, message, category, filename, lineno,
                        file=sys.stderr):
        self.failUnlessEqual(alreadyInstalledMsg, str(message))
        self.warned = True
        

class TestZopeless(PgTestCase):
    dbname = 'ftest_tmp'

    def setUp(self):
        super(TestZopeless, self).setUp()
        self.tm = initZopeless(dbname=self.dbname, dbhost='')
        MoreBeer.createTable()
        self.tm.commit()

    def tearDown(self):
        self.tm.uninstall()
        super(TestZopeless, self).tearDown()

    def test_simple(self):
        # Create a few MoreBeers and make sure we can access them
        b = MoreBeer(name='Victoria Bitter')
        id1 = b.id
        b = MoreBeer(name='XXXX')
        id2 = b.id

        b = MoreBeer.get(id1)
        b.rating = 3
        b = MoreBeer.get(id2)
        b.rating = 2

        b = MoreBeer.get(id1)
        self.failUnlessEqual(b.rating, 3)


    def test_multipleTransactions(self):
        # Here we create a MoreBeer and make modifications in a number
        # of different transactions

        b = MoreBeer(name='Victoria Bitter')
        id = b.id
        self.tm.commit()

        b = MoreBeer.get(id)
        self.failUnlessEqual(b.name, 'Victoria Bitter')
        b.rating = 4
        self.tm.commit()

        b = MoreBeer.get(id)
        self.failUnlessEqual(b.rating, 4)
        b.rating = 5
        self.tm.commit()

        b = MoreBeer.get(id)
        self.failUnlessEqual(b.rating, 5)
        b.rating = 2
        self.tm.abort()

        b = MoreBeer.get(id)
        self.failUnlessEqual(b.rating, 5)
        b.rating = 4
        self.tm.commit()

        b = MoreBeer.get(id)
        self.failUnlessEqual(b.rating, 4)

    def test_threads(self):
        # Here we create a number of MoreBeers in seperate threads
        def doit():
            #self.tm.begin()
            b = MoreBeer(name=beer_name)
            b.rating = beer_rating
            self.tm.commit()

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
        beers = list(MoreBeer.select())
        self.failUnlessEqual(len(beers), 2)
        self.tm.commit()

    def test_exception(self):

        # We have observed if a database transaction ends badly, it is
        # not reset for future transactions. To test this, we cause
        # a database exception
        MoreBeer(name='Victoria Bitter')
        try:
            MoreBeer(name='Victoria Bitter')
        except psycopg.IntegrityError:
            pass
        else:
            self.fail('Unique constraint was not triggered')
        self.tm.abort()

        # Now start a new transaction and see if we can do anything
        self.tm.begin()
        MoreBeer(name='Singa')


def test_suite():
    # Tests disabled - no gain
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestZopeless))
    suite.addTest(unittest.makeSuite(TestInitZopeless))
    return suite

if __name__ == '__main__':
    unittest.main()


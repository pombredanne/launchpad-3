"""
Tests to make sure that initZopeless works as expected.
"""
from threading import Thread
import unittest
import warnings

import psycopg2
from sqlobject import StringCol, IntCol
from zope.testing.doctest import DocTestSuite

from canonical.database.sqlbase import SQLBase, alreadyInstalledMsg
from canonical.ftests.pgsql import PgTestSetup
from canonical.lp import initZopeless
from canonical.testing import LaunchpadLayer


class MoreBeer(SQLBase):
    '''Simple SQLObject class used for testing'''
    # test_sqlos defines a Beer SQLObject already, so we call this one
    # MoreBeer to avoid confusing SQLObject.
    _columns = [
        StringCol('name', alternateID=True, notNull=True),
        IntCol('rating', default=None),
        ]


class TestInitZopeless(unittest.TestCase):
    layer = LaunchpadLayer

    def test_initZopelessTwice(self):
        # Hook the warnings module, so we can verify that we get the expected
        # warning.
        warn_explicit = warnings.warn_explicit
        warnings.warn_explicit = self.expectedWarning
        self.warned = False
        try:
            # Calling initZopeless with the same arguments twice should return
            # the exact same object twice, but also emit a warning.
            try:
                tm1 = initZopeless(dbname=PgTestSetup().dbname, dbhost='',
                        dbuser='launchpad')
                tm2 = initZopeless(dbname=PgTestSetup().dbname, dbhost='',
                        dbuser='launchpad')
                self.failUnless(tm1 is tm2)
                self.failUnless(self.warned)
            finally:
                tm1.uninstall()
        finally:
            # Put the warnings module back the way we found it.
            warnings.warn_explicit = warn_explicit

    def expectedWarning(self, message, category, filename, lineno,
                        module=None, registry=None):
        self.failUnlessEqual(alreadyInstalledMsg, str(message))
        self.warned = True


class TestZopeless(unittest.TestCase):
    layer = LaunchpadLayer

    def setUp(self):
        self.tm = initZopeless(dbname=PgTestSetup().dbname,
                               dbuser='launchpad')
        MoreBeer.createTable()
        self.tm.commit()

    def tearDown(self):
        self.tm.uninstall()

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
            self.tm.begin()
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
        beers = MoreBeer.select()
        self.failUnlessEqual(beers.count(), 2)
        self.tm.commit()

    def test_exception(self):

        # We have observed if a database transaction ends badly, it is
        # not reset for future transactions. To test this, we cause
        # a database exception
        MoreBeer(name='Victoria Bitter')
        try:
            MoreBeer(name='Victoria Bitter')
        except psycopg2.DatabaseError:
            pass
        else:
            self.fail('Unique constraint was not triggered')
        self.tm.abort()

        # Now start a new transaction and see if we can do anything
        self.tm.begin()
        MoreBeer(name='Singa')

    def test_externalChange(self):
        # Make a change
        MoreBeer(name='Victoria Bitter')

        # Commit our local change
        self.tm.commit()

        # Make another change from a non-SQLObject connection, and commit that
        conn = psycopg2.connect('dbname=' + PgTestSetup().dbname)
        cur = conn.cursor()
        cur.execute("BEGIN TRANSACTION;")
        cur.execute("UPDATE MoreBeer SET rating=4 "
                    "WHERE name='Victoria Bitter';")
        cur.execute("COMMIT TRANSACTION;")
        cur.close()
        conn.close()

        # We should now be able to see the external change in our connection
        self.failUnlessEqual(4, MoreBeer.byName('Victoria Bitter').rating)


def test_isZopeless():
    """
    >>> from canonical.lp import isZopeless

    >>> isZopeless()
    False

    >>> PgTestSetup().setUp()
    >>> isZopeless()
    False

    >>> tm = initZopeless(dbname=PgTestSetup().dbname,
    ...     dbhost='', dbuser='launchpad')
    >>> isZopeless()
    True

    >>> tm.uninstall()
    >>> isZopeless()
    False

    >>> PgTestSetup().tearDown()
    >>> isZopeless()
    False

    """

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestZopeless))
    suite.addTest(unittest.makeSuite(TestInitZopeless))
    doctests = DocTestSuite()
    doctests.layer = LaunchpadLayer
    suite.addTests(doctests)
    return suite

if __name__ == '__main__':
    unittest.main()


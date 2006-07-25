"""
Tests to make sure that initZopeless works as expected.
"""
import unittest, warnings, sys, psycopg
from threading import Thread

from zope.testing.doctest import DocTestSuite
from sqlobject import StringCol, IntCol

from canonical.lp import initZopeless
from canonical.database.sqlbase import (
        SQLBase, alreadyInstalledMsg, cursor, connect, DEFAULT_ISOLATION,
        AUTOCOMMIT_ISOLATION, READ_COMMITTED_ISOLATION, SERIALIZABLE_ISOLATION,
        )
from canonical.ftests.pgsql import PgTestCase, PgTestSetup
from canonical.functional import FunctionalTestSetup, ZopelessLayer


class MoreBeer(SQLBase):
    '''Simple SQLObject class used for testing'''
    # test_sqlos defines a Beer SQLObject already, so we call this one MoreBeer
    # to avoid confusing SQLObject.
    _columns = [
        StringCol('name', alternateID=True, notNull=True),
        IntCol('rating', default=None),
        ]


class TestInitZopeless(PgTestCase):
    dbname = 'ftest_tmp'
    layer = ZopelessLayer
    
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
                tm1 = initZopeless(dbname=self.dbname, dbhost='',
                        dbuser='launchpad')
                tm2 = initZopeless(dbname=self.dbname, dbhost='',
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
    layer = ZopelessLayer

    def setUp(self):
        PgTestSetup().setUp()
        self.dbname = PgTestSetup().dbname
        self.tm = initZopeless(dbname=self.dbname, dbuser='launchpad')
        MoreBeer.createTable()
        self.tm.commit()

    def tearDown(self):
        self.tm.uninstall()
        PgTestSetup().tearDown()

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
        except psycopg.DatabaseError:
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
        conn = psycopg.connect('dbname=' + self.dbname)
        cur = conn.cursor()
        cur.execute("BEGIN TRANSACTION;")
        cur.execute("UPDATE MoreBeer SET rating=4 "
                    "WHERE name='Victoria Bitter';")
        cur.execute("COMMIT TRANSACTION;")
        cur.close()
        conn.close()

        # We should now be able to see the external change in our connection
        self.failUnlessEqual(4, MoreBeer.byName('Victoria Bitter').rating)


class TestZopelessIsolation(unittest.TestCase):
    layer = ZopelessLayer

    def setUp(self):
        PgTestSetup().setUp()
        self.dbname = PgTestSetup().dbname

    def tearDown(self):
        PgTestSetup().tearDown()

    def _test_isolation(self, isolation, isolation_string):
        # Test that PostgreSQL reports the isolation level we expect
        # and that it sticks across transactions.
        ztm = initZopeless(
                dbname=self.dbname, dbuser='launchpad',
                isolation=isolation
                )
        try:
            cur = cursor()
            cur.execute("SHOW transaction_isolation")
            self.failUnlessEqual(isolation_string, cur.fetchone()[0])
            ztm.abort()

            cur = cursor()
            cur.execute("SHOW transaction_isolation")
            self.failUnlessEqual(isolation_string, cur.fetchone()[0])
            ztm.commit()

            cur = cursor()
            cur.execute("SHOW transaction_isolation")
            self.failUnlessEqual(isolation_string, cur.fetchone()[0])
            ztm.abort()
        finally:
            ztm.uninstall()

    def test_readCommitted(self):
        self._test_isolation(READ_COMMITTED_ISOLATION, 'read committed')

    def test_serializable(self):
        self._test_isolation(SERIALIZABLE_ISOLATION, 'serializable')

    def test_default(self):
        self._test_isolation(DEFAULT_ISOLATION, 'serializable')

    def test_autocommit(self):
        # First test normal behavior
        ztm = initZopeless(dbname=self.dbname, dbuser='launchpad')
        try:
            cur = cursor()
            cur.execute("CREATE TABLE whatever (x integer)")
            ztm.abort()

            # This will fail, as the table creation has been rolled back
            cur = cursor()
            try:
                cur.execute("INSERT INTO whatever VALUES (1)")
            except psycopg.Error:
                pass
            else:
                self.fail("Default connection is autocommitting!")
        finally:
            ztm.uninstall()

        ztm = initZopeless(
                dbname=self.dbname, dbuser='launchpad',
                isolation=AUTOCOMMIT_ISOLATION
                )
        try:
            cur = cursor()
            cur.execute("CREATE TABLE whatever (x integer)")
            ztm.abort()

            # This will fail if the table creation has been rolled back
            cur = cursor()
            cur.execute("INSERT INTO whatever VALUES (1)")
            ztm.abort()
        finally:
            ztm.uninstall()


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
    suite.addTest(unittest.makeSuite(TestZopelessIsolation))
    doctests = DocTestSuite()
    doctests.layer = ZopelessLayer
    suite.addTests(doctests)
    return suite

if __name__ == '__main__':
    unittest.main()


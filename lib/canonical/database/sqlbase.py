from sqlos import SQLOS
from sqlos.adapter import PostgresAdapter
from sqlobject.sqlbuilder import sqlrepr
from sqlobject.styles import Style
from datetime import datetime, date, time
from sqlobject import connectionForURI
import thread, warnings

__all__ = ['SQLBase', 'quote', 'quote_like', 'ZopelessTransactionManager']

class LaunchpadStyle(Style):
    """A SQLObject style for launchpad. 
    
    Python attributes and database columns are lowercase.
    Class names and database tables are MixedCase. Using this style should
    simplify SQLBase class definitions since more defaults will be correct.
    """

    def pythonAttrToDBColumn(self, attr):
        return attr

    def dbColumnToPythonAttr(self, col):
        return col

    def pythonClassToDBTable(self, className):
        return className

    def dbTableToPythonClass(self, table):
        raise NotImplementedError, \
                "Our naming convention prohibits converting table to class"
        return table

    def idForTable(self, table):
        return 'id'

    def pythonClassToAttr(self, className):
        return className.lower()


class SQLBase(SQLOS):
    """Base class to use instead of SQLObject/SQLOS.
    
    Annoying hack to allow us to use SQLOS features in Zope, and plain
    SQLObject outside of Zope.  ("Zope" in this case means the Zope 3 Component
    Architecture, i.e. the basic suite of services should be accessible via
    zope.component.getService)

    By default, this will act just like SQLOS.  Use a
    ZopelessTransactionManager object to disable all the tricksy
    per-thread connection stuff that SQLOS does.
    """
    _style = LaunchpadStyle()
    
    def reset(self):
        if not self._SO_createValues:
            return
        self._SO_writeLock.acquire()
        try:
            self.dirty = False
            self._SO_createValues = {}
        finally:
            self._SO_writeLock.release()

    def __int__(self):
        '''Cast to integer, returning the primary key value'''
        # All our SQLBase objects have an integer primary key called 'id'
        return self.id


class _ZopelessConnectionDescriptor(object):
    def __init__(self, connectionURI, sqlosAdapter=PostgresAdapter,
                 debug=False):
        self.connectionURI = connectionURI
        self.sqlosAdapter = sqlosAdapter
        self.transactions = {}
        self.debug = debug

    def __get__(self, inst, cls=None):
        tid = thread.get_ident()
        if tid not in self.transactions:
            conn = connectionForURI(self.connectionURI).makeConnection()
            adapted = self.sqlosAdapter(conn)
            adapted.debug = self.debug
            self.transactions[tid] = adapted.transaction()
        return self.transactions[tid]

    def __set__(self, inst, value):
        '''Do nothing
        
        This used to issue a warning but it seems to be spurious.

        '''
        pass
        #import warnings
        #warnings.warn("Something tried to set a _connection.  Ignored.")

    def install(cls, connectionURI, sqlClass=SQLBase, debug=False):
        if isinstance(sqlClass.__dict__.get('_connection'),
                _ZopelessConnectionDescriptor):
            # ZopelessTransactionManager.__new__ should now prevent this from
            # happening, so raise an error if it somehow does anyway.
            raise RuntimeError, "Already installed _connection descriptor."
        cls.sqlClass = sqlClass
        sqlClass._connection = cls(connectionURI, debug=debug)
    install = classmethod(install)

    def uninstall(cls):
        # Explicitly close all connections we opened.
        descriptor = cls.sqlClass.__dict__.get('_connection')
        for trans in descriptor.transactions.itervalues():
            trans.releaseConnection(trans._connection, explicit=True)
            trans._dbConnection._connection.close()

        # Remove the _connection descriptor.  This assumes there was no
        # _connection in this particular class to start with (which is true for
        # SQLBase, but wouldn't be true for SQLOS)
        del cls.sqlClass._connection
    uninstall = classmethod(uninstall)
        

alreadyInstalledMsg = ("A ZopelessTransactionManager with these settings is "
"already installed.  This is probably caused by calling initZopeless twice.")


class ZopelessTransactionManager(object):
    """Object to use in scripts and tests if you want transactions.
    This behaviour used to be in SQLBase, but as more methods and
    attributes became needed, a new class was created to avoid
    namespace pollution.

    Quick & dirty doctest:
    XXX: DISABLED!  This should be turned into a functional test.

    #>>> from canonical.lp import dbname
    #>>> ztm = ZopelessTransactionManager('postgres:///' + dbname)
    #
    #The _connection attribute of SQLBase should now be a descriptor that returns
    #sqlobject.dbconnection.Transaction instances.
    #
    #>>> from sqlobject.dbconnection import Transaction
    #>>> t1 = SQLBase._connection
    #>>> isinstance(t1, Transaction)
    #True
    #
    #And it should give the same connection to the same thread over multiple
    #accesses.
    #
    #>>> t2 = SQLBase._connection
    #>>> t1 is t2
    #True
    #
    #And different in different threads:
    #
    #>>> from threading import Thread, Lock, Event
    #>>> l = []
    #>>> t = Thread(target=lambda: l.append(SQLBase._connection))
    #>>> t.start()
    #>>> t.join()
    #>>> l[0] is not t1
    #True

    XXX: This bit is overly dependent on the db...
    Show that concurrent transactions in different threads work correctly
    #>>> from sqlobject import StringCol
    #>>> class TestPerson(SQLBase):
    #...     _table = 'Person'
    #...     displayname = StringCol()
    #...     givenname = StringCol()
    #...
    #>>> mark = TestPerson.selectBy(displayname='Mark Shuttleworth')[0]
    #>>> mark.id == 1
    #True
    #>>> mark.givenname = 'Markk'
    #>>> mark.givenname = 'Mark'
    #>>> ztm.commit()
    #>>> ztm.commit()
    
    #>>> event = Event()
    #>>> event2 = Event()
    #>>> def foo(TestPerson=TestPerson, ztm=ztm, event=event, event2=event2):
    #...     andrew = TestPerson.selectBy(displayname='Andrew Bennetts')[0]
    #...     
    #...     andrew.givenname = 'Andreww'
    #...     andrew.givenname = 'Andrew'
    #...     event.set()
    #...     event2.wait()
    #...     ztm.commit()
    #...
    #>>> t = Thread(target=foo)
    #>>> t.start()
    #>>> event.wait()
    #>>> mark = TestPerson.selectBy(displayname='Mark Shuttleworth')[0]
    #>>> mark.id == 1
    #True
    #>>> mark.givenname = 'Markk'
    #>>> mark.givenname = 'Mark'
    #>>> ztm.commit()
    #>>> event2.set()
    #>>> 
    #>>> t.join()

    Cleanup -- make sure this doctest leaves things in the same state it found
    them.

    #>>> ztm.uninstall()

    """

    _installed = None
    alreadyInited = False

    def __new__(cls, connectionURI, sqlClass=SQLBase, debug=False):
        if cls._installed is not None:
            if (cls._installed.connectionURI != connectionURI or
                cls._installed.sqlClass != sqlClass or
                cls._installed.debug != debug):
                    raise ConflictingTransactionManagerError(
                            "A ZopelessTransactionManager with different "
                            "settings is already installed"
                    )
            # There's an identical ZopelessTransactionManager already installed,
            # so return that one, but also emit a warning.
            warnings.warn(alreadyInstalledMsg, stacklevel=2)
            return cls._installed
        cls._installed = object.__new__(cls, connectionURI, sqlClass, debug)
        return cls._installed

    def __init__(self, connectionURI, sqlClass=SQLBase, debug=False):
        # For some reason, Python insists on calling __init__ on anything
        # returned from __new__, even if it's not a newly constructed object
        # (i.e. type.__call__ calls __init__, rather than object.__new__ like
        # you'd expect).
        if self.alreadyInited:
            return
        self.alreadyInited = True
        
        # XXX: Importing a module-global and assigning it as an instance
        #      attribute smells funny.  Why not just use transaction.manager
        #      instead of self.manager?
        from transaction import manager
        self.manager = manager
        _ZopelessConnectionDescriptor.install(connectionURI, debug=debug)
        self.sqlClass = sqlClass
        # The next two instance variables are used for the check in __new__
        self.connectionURI = connectionURI
        self.debug = debug
        #self.cls._connection = adapter(self.connection.makeConnection())
        #self.dm = self.cls._connection._dm
        #self.begin()

    def uninstall(self):
        _ZopelessConnectionDescriptor.uninstall()
        # We delete self.sqlClass to make sure this instance isn't still
        # used after uninstall was called, which is a little bit of a hack.
        self.manager.free(self.manager.get())
        del self.sqlClass 
        self.__class__._installed = None

    def _dm(self):
        return self.sqlClass._connection._dm

    def begin(self):
        txn = self.manager.begin()
        txn.join(self._dm())

    def commit(self, sub=False):
        self.manager.get().commit(sub)
        self._clearCache()
        self.begin()

    def abort(self, sub=False):
        objects = list(self._dm().objects)
        self.manager.get().abort(sub)
        for obj in objects:
            obj.reset()
            obj.expire()
        self._clearCache()
        self.begin()

    def _clearCache(self):
        """Clear SQLObject's object cache for the current connection."""
        # XXX: There is a different hack for (I think?) similar reasons in
        #      canonical.publication.  This should probably share code with
        #      that one.
        #        - Andrew Bennetts, 2005-02-01
        for c in SQLBase._connection.cache.allSubCaches():
            c.clear()


def quote(x):
    r"""Quote a variable ready for inclusion into an SQL statement.
    Note that you should use quote_like to create a LIKE comparison.

    Basic SQL quoting works

    >>> quote(1)
    '1'
    >>> quote(1.0)
    '1.0'
    >>> quote("hello")
    "'hello'"

    Timezone handling is not implemented, since all timestamps should
    be UTC anyway.

    >>> from datetime import datetime, date, time
    >>> quote(datetime(2003, 12, 4, 13, 45, 50))
    "'2003-12-04 13:45:50'"
    >>> quote(date(2003, 12, 4))
    "'2003-12-04'"
    >>> quote(time(13, 45, 50))
    "'13:45:50'"

    Note that we have to special case datetime handling, as
    SQLObject's quote function is quite broken ( http://tinyurl.com/4bk8p )

    >>> sqlrepr(datetime(2003, 12, 4, 13, 45, 50), 'postgres')
    "'2003-12-04'"

    """
    if isinstance(x, datetime):
        return "'%s'" % x
    return sqlrepr(x, 'postgres')

def quote_like(x):
    r"""Quote a variable ready for inclusion in a SQL statement's LIKE clause

    TODO: Including the single quotes was a stupid decision.
    -- StuartBishop 2004/11/24

    To correctly generate a SELECT using a LIKE comparision, we need
    to make use of the SQL string concatination operator '||' and the
    quote_like method to ensure that any characters with special meaning
    to the LIKE operator are correctly escaped.

    >>> "SELECT * FROM mytable WHERE mycol LIKE '%%' || %s || '%%'" \
    ...     % quote_like('%')
    "SELECT * FROM mytable WHERE mycol LIKE '%' || '\\\\%' || '%'"

    Note that we need 2 backslashes to quote, as per the docs on
    the LIKE operator. This is because, unless overridden, the LIKE
    operator uses the same escape character as the SQL parser.

    >>> quote_like('100%')
    "'100\\\\%'"
    >>> quote_like('foobar_alpha1')
    "'foobar\\\\_alpha1'"
    >>> quote_like('hello')
    "'hello'"

    Only strings are supported by this method.

    >>> quote_like(1)
    Traceback (most recent call last):
        [...]
    TypeError: Not a string (<type 'int'>)

    """
    if not isinstance(x, basestring):
        raise TypeError, 'Not a string (%s)' % type(x)
    return quote(x).replace('%', r'\\%').replace('_', r'\\_')


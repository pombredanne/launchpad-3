# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import psycopg
from sqlos import SQLOS
from sqlos.adapter import PostgresAdapter
from sqlobject.sqlbuilder import sqlrepr
from sqlobject.styles import Style
from datetime import datetime
from sqlobject import connectionForURI
import thread, warnings
import time

from canonical.config import config

__all__ = ['SQLBase', 'quote', 'quote_like', 'sqlvalues',
           'ZopelessTransactionManager', 'ConflictingTransactionManagerError']


# First, let's monkey-patch SQLObject a little, to stop its getID function from
# returning None for security-proxied SQLObjects!
import zope.security.proxy
import sqlobject.main
sqlobject.main.isinstance = zope.security.proxy.isinstance


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

    # dsilvers: 20050322: If you take this method out; then RelativeJoin
    # instances in our SQLObject classes cause the following error:
    # AttributeError: 'LaunchpadStyle' object has no attribute 'tableReference'
    def tableReference(self, table):
        """Return the tablename mapped for use in RelativeJoin statements."""
        return table.__str__()


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
    """Descriptor for SQLObject._connection.

    It provides per-thread transactions.  If implicitActivate is set (the
    default), then these transactions will be created on-demand if they don't
    already exist.  If implicitActivate is not set, then this will return None
    for a thread until `_activate` is called, and after `_deactivate` is called.
    """
    def __init__(self, connectionURI, sqlosAdapter=PostgresAdapter,
                 debug=False, implicitActivate=True, reconnect=False):
        self.connectionURI = connectionURI
        self.sqlosAdapter = sqlosAdapter
        self.transactions = {}
        self.debug = debug
        self.implicitActivate = implicitActivate
        self.reconnect = reconnect

    def _reconnect(self):
        first = True
        conn = None
        while True:
            if first:
                first = False
            else:
                # Sleep so that we aren't completely hammering things.
                time.sleep(1)
                
            # Be neat and tidy: try to close the remains of any previous
            # attempt.
            if conn is not None:
                try:
                    conn.close()
                except psycopg.Error:
                    pass
                conn = None
                
            # Make a connection, and a cursor.  If this fails, just loop and try
            # again.
            try:
                conn = connectionForURI(self.connectionURI).makeConnection()
                cur = conn.cursor()
            except psycopg.Error:
                continue

            # Check that the cursor really works, making sure to close it
            # afterwards.  If it doesn't, back to the top...
            try:
                try:
                    cur.execute('SELECT 1;')
                except psycopg.Error:
                    continue
            finally:
                cur.close()

            # Great!  We have a working connection.  We're done.
            return conn

    def _activate(self):
        """Activate SQLBase._connection for the current thread."""
        tid = thread.get_ident()
        assert tid not in self.transactions, (
            "Already activated the connection descriptor for this thread.")

        # Build a connection (retrying if necessary)
        if self.reconnect:
            conn = self._reconnect()
        else:
            conn = connectionForURI(self.connectionURI).makeConnection()

        # Wrap it in SQLOS's loving arms.
        adapted = self.sqlosAdapter(conn)
        adapted.debug = self.debug

        # Create a Transaction, and put it in the transactions dict.
        self.transactions[tid] = adapted.transaction()

    def _deactivate(self):
        """Deactivate SQLBase._connection for the current thread."""
        del self.transactions[thread.get_ident()]
    
    def __get__(self, inst, cls=None):
        """Return the Transaction object for this thread if it exists, or None."""
        tid = thread.get_ident()
        if self.implicitActivate and tid not in self.transactions:
            self._activate()
        return self.transactions.get(thread.get_ident(), None)

    def __set__(self, inst, value):
        '''Do nothing
        
        This used to issue a warning but it seems to be spurious.

        '''
        pass
        #import warnings
        #warnings.warn("Something tried to set a _connection.  Ignored.")

    def install(cls, connectionURI, sqlClass=SQLBase, debug=False,
                implicitActivate=True, reconnect=False):
        if isinstance(sqlClass.__dict__.get('_connection'),
                _ZopelessConnectionDescriptor):
            # ZopelessTransactionManager.__new__ should now prevent this from
            # happening, so raise an error if it somehow does anyway.
            raise RuntimeError, "Already installed _connection descriptor."
        cls.sqlClass = sqlClass
        descriptor = cls(connectionURI, debug=debug,
                         implicitActivate=implicitActivate, reconnect=reconnect)
        sqlClass._connection = descriptor
        return descriptor
    install = classmethod(install)

    def uninstall(cls):
        # Explicitly close all connections we opened.
        descriptor = cls.sqlClass.__dict__.get('_connection')
        for trans in descriptor.transactions.itervalues():
            try:
                trans.rollback()
            except psycopg.Error:
                pass
            trans._dbConnection._connection.close()

        # Remove the _connection descriptor.  This assumes there was no
        # _connection in this particular class to start with (which is true for
        # SQLBase, but wouldn't be true for SQLOS)
        del cls.sqlClass._connection
    uninstall = classmethod(uninstall)
        

alreadyInstalledMsg = ("A ZopelessTransactionManager with these settings is "
"already installed.  This is probably caused by calling initZopeless twice.")


class ConflictingTransactionManagerError(Exception):
    pass


class ZopelessTransactionManager(object):
    """Object to use in scripts and tests if you want transactions.

    This behaviour used to be in SQLBase, but as more methods and
    attributes became needed, a new class was created to avoid
    namespace pollution.
    """

    _installed = None
    alreadyInited = False

    def __new__(cls, connectionURI, sqlClass=SQLBase, debug=False,
                implicitBegin=True):
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
        cls._installed = object.__new__(cls, connectionURI, sqlClass, debug,
                                        implicitBegin)
        return cls._installed

    def __init__(self, connectionURI, sqlClass=SQLBase, debug=False,
                 implicitBegin=True):
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
        desc = _ZopelessConnectionDescriptor.install(
            connectionURI, debug=debug, implicitActivate=implicitBegin,
            reconnect=not implicitBegin)
        self.sqlClass = sqlClass
        self.desc = desc
        # The next two instance variables are used for the check in __new__
        self.connectionURI = connectionURI
        self.debug = debug
        self.implicitBegin = implicitBegin
        if self.implicitBegin:
            self.begin()

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
        if not self.implicitBegin:
            self.desc._activate()
        _clearCache()
        txn = self.manager.begin()
        txn.join(self._dm())

    def commit(self, sub=False):
        self.manager.get().commit(sub)

        # We always remove the existing transaction & connection, for
        # simplicity.  SQLObject does connection pooling, and we don't have any
        # indication that reconnecting every transaction would be a performance
        # problem anyway.
        self.desc._deactivate()

        if self.implicitBegin:
            self.begin()

    def abort(self, sub=False):
        objects = list(self._dm().objects)
        self.manager.get().abort(sub)
        for obj in objects:
            obj.reset()
            obj.expire()
        self.desc._deactivate()
        if self.implicitBegin:
            self.begin()


def _clearCache():
    """Clear SQLObject's object cache for the current connection."""
    # XXX: There is a different hack for (I think?) similar reasons in
    #      canonical.publication.  This should probably share code with
    #      that one.
    #        - Andrew Bennetts, 2005-02-01

    # Don't break if _connection is a FakeZopelessConnectionDescriptor
    if getattr(SQLBase._connection, 'cache', None) is not None:
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
    >>> quote("'hello'")
    "'''hello'''"
    >>> quote(r"\'hello")
    "'\\\\''hello'"

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

def sqlvalues(*values, **kwvalues):
    """Return a tuple of converted sql values for each value in some_tuple.

    This safely quotes strings, or gives representations of dbschema items,
    for example.

    Use it when constructing a string for use in a SELECT.  Always use
    %s as the replacement marker.

      ('SELECT foo from Foo where bar = %s and baz = %s'
       % sqlvalues(BugSeverity.CRITICAL, 'foo'))

    >>> sqlvalues()
    Traceback (most recent call last):
    ...
    TypeError: Use either positional or keyword values with sqlvalue.
    >>> sqlvalues(1)
    ('1',)
    >>> sqlvalues(1, "bad ' string")
    ('1', "'bad '' string'")

    You can also use it when using dict-style substitution.

    >>> sqlvalues(foo=23)
    {'foo': '23'}

    However, you cannot mix the styles.

    >>> sqlvalues(14, foo=23)
    Traceback (most recent call last):
    ...
    TypeError: Use either positional or keyword values with sqlvalue.

    """
    if (values and kwvalues) or (not values and not kwvalues):
        raise TypeError(
            "Use either positional or keyword values with sqlvalue.")
    if values:
        return tuple([quote(item) for item in values])
    elif kwvalues:
        return dict([(key, quote(value)) for key, value in kwvalues.items()])

def quoteIdentifier(identifier):
    r'''Quote an identifier, such as a table name.
    
    In SQL, identifiers are quoted using " rather than ' which is reserved
    for strings.

    >>> print quoteIdentifier('hello')
    "hello"
    >>> print quoteIdentifier("'")
    "'"
    >>> print quoteIdentifier('"')
    """"
    >>> print quoteIdentifier("\\")
    "\"
    >>> print quoteIdentifier('\\"')
    "\"""
    '''
    return '"%s"' % identifier.replace('"','""')

def flush_database_updates():
    """Flushes all pending database updates for the current connection.
    
    When SQLObject's _lazyUpdate flag is set, then it's possible to have
    changes written to objects that aren't flushed to the database, leading to
    inconsistencies when doing e.g.::
        
        # Assuming the Beer table already has a 'Victoria Bitter' row...
        assert Beer.select("name LIKE 'Vic%'").count() == 1  # This will pass
        beer = Beer.byName('Victoria Bitter')
        beer.name = 'VB'
        assert Beer.select("name LIKE 'Vic%'").count() == 0  # This will fail

    To avoid this problem, use this function::

        # Assuming the Beer table already has a 'Victoria Bitter' row...
        assert Beer.select("name LIKE 'Vic%'").count() == 1  # This will pass
        beer = Beer.byName('Victoria Bitter')
        beer.name = 'VB'
        flush_database_updates()
        assert Beer.select("name LIKE 'Vic%'").count() == 0  # This will pass

    """
    # XXX: turn that comment into a doctest
    #        - Andrew Bennetts, 2005-02-16
    # https://launchpad.ubuntu.com/malone/bugs/452
    #        - Brad Bollenbach, 2005-04-20
    for object in list(SQLBase._connection._dm.objects):
        object.syncUpdate()


# Some helpers intended for use with initZopeless.  These allow you to avoid
# passing the transaction manager all through your code.  Also, this begin()
# does an implicit rollback() for convenience. 
# XXX: Make these use and work with Zope 3's transaction machinery instead!
#        - Andrew Bennetts, 2005-02-11

def begin():
    """Begins a transaction, aborting the current one if necessary."""
    transaction = SQLBase._connection
    if transaction is None:
        ZopelessTransactionManager._installed.begin()
        return
    if not transaction._obsolete:
        # XXX: This perhaps should raise a warning?
        #        - Andrew Bennetts, 2005-02-11
        transaction.rollback()
    _clearCache()
    transaction.begin()

def rollback():
    SQLBase._connection.rollback()

def commit():
    SQLBase._connection.commit()

def connect(user, dbname=None):
    """Return a fresh DB-API connecction to the database.

    Use None for the user to connect as the default PostgreSQL user.
    This is not the default because the option should be rarely used.

    Default database name is the one specified in the main configuration file.
    """
    con_str = 'dbname=%s' % (dbname or config.dbname)
    if user:
        con_str += ' user=%s' % user
    if config.dbhost:
        con_str += ' host=%s' % config.dbhost
    return psycopg.connect(con_str)

def cursor():
    '''Return a cursor from the current database connection.

    This is useful for code that needs to issue database queries
    directly rather than using the SQLObject interface
    '''
    return SQLBase._connection._connection.cursor()
    

class FakeZopelessConnectionDescriptor(_ZopelessConnectionDescriptor):
    """A helper class for testing.
    
    Use this if you want to know if commit or rollback was called.
    """
    _obsolete = True
    begun = False
    rolledback = False
    committed = False

    def __get__(self, inst, cls=None):
        return self

    def begin(self):
        self.begun = True

    def rollback(self):
        self.rolledback = True

    def commit(self):
        self.committed = True



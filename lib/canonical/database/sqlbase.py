# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import psycopg
import thread
import warnings
import time
from datetime import datetime

from sqlos import SQLOS
from sqlos.adapter import PostgresAdapter

from sqlobject import connectionForURI, SQLObjectNotFound
from sqlobject.sqlbuilder import sqlrepr
from sqlobject.styles import Style

from zope.interface import implements

from canonical.config import config
from canonical.database.interfaces import ISQLBase

__all__ = ['SQLBase', 'quote', 'quote_like', 'quoteIdentifier', 'sqlvalues',
           'ZopelessTransactionManager', 'ConflictingTransactionManagerError',
           'flush_database_updates', 'flush_database_caches', 'cursor',
           'begin', 'commit', 'rollback', 'alreadyInstalledMsg', 'connect',
           'AUTOCOMMIT_ISOLATION', 'READ_COMMITTED_ISOLATION',
           'SERIALIZABLE_ISOLATION', 'DEFAULT_ISOLATION',
           'clear_current_connection_cache', 'expire_from_cache']

# As per badly documented psycopg 1 constants
AUTOCOMMIT_ISOLATION=0
READ_COMMITTED_ISOLATION=1
SERIALIZABLE_ISOLATION=3
# Default we want for scripts, and the PostgreSQL default. Note psycopg1 will
# use SERIALIZABLE unless we override, but psycopg2 will not.
DEFAULT_ISOLATION=READ_COMMITTED_ISOLATION

# First, let's monkey-patch SQLObject a little:
import zope.security.proxy
import sqlobject.main
import sqlobject.dbconnection
# 1. Make its getID function work for proxied SQLObjects
sqlobject.main.isinstance = zope.security.proxy.isinstance
# 2. Make _SO_columnClause use the right isinstance so that Proxied
# SQLObjects can be used in the RHS of a select*By expression (for
# instance, selectBy(foo=obj))
sqlobject.dbconnection.isinstance = zope.security.proxy.isinstance


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
    implements(ISQLBase)
    _style = LaunchpadStyle()
    _randomiseOrder = config.randomise_select_results
    # Silence warnings in linter script, which complains about all
    # SQLBase-derived objects missing an id.
    id = None

    def reset(self):
        if not self._SO_createValues:
            return
        self._SO_writeLock.acquire()
        try:
            self.dirty = False
            self._SO_createValues = {}
        finally:
            self._SO_writeLock.release()


class _ZopelessConnectionDescriptor(object):
    """Descriptor for SQLObject._connection.

    It provides per-thread transactions.  If implicitActivate is set (the
    default), then these transactions will be created on-demand if they don't
    already exist.  If implicitActivate is not set, then this will return None
    for a thread until `_activate` is called, and after `_deactivate` is called.
    """
    def __init__(self, connectionURI, sqlosAdapter=PostgresAdapter,
                 debug=False, implicitActivate=True, reconnect=False,
                 isolation=DEFAULT_ISOLATION):
        self.connectionURI = connectionURI
        self.sqlosAdapter = sqlosAdapter
        self.transactions = {}
        self.debug = debug
        self.implicitActivate = implicitActivate
        self.reconnect = reconnect
        self.alreadyActivated = False
        self.isolation = isolation

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

            # Great!  We have a working connection.  We're done once we
            # have reset the transaction isolation level
            conn.set_isolation_level(self.isolation)
            return conn

    def _activate(self):
        """Activate SQLBase._connection for the current thread."""
        tid = thread.get_ident()
        assert tid not in self.transactions, (
            "Already activated the connection descriptor for this thread.")

        # Build a connection (retrying if necessary)
        if self.reconnect and self.alreadyActivated:
            conn = self._reconnect()
        else:
            conn = connectionForURI(self.connectionURI).makeConnection()
            conn.set_isolation_level(self.isolation)
            self.alreadyActivated = True

        # Wrap it in SQLOS's loving arms.
        adapted = self.sqlosAdapter(conn)
        adapted.debug = self.debug

        # Create a Transaction, and put it in the transactions dict.
        self.transactions[tid] = adapted.transaction()

    def _deactivate(self):
        """Deactivate SQLBase._connection for the current thread."""
        tid = thread.get_ident()
        assert tid in self.transactions, (
            "Deactivating a non-active connection descriptor for this thread.")
        self.transactions[tid]._connection.close()
        self.transactions[tid]._makeObsolete()
        del self.transactions[tid]

    def __get__(self, inst, cls=None):
        """Return Transaction object for this thread (if it exists) or None."""
        tid = thread.get_ident()
        if self.implicitActivate and tid not in self.transactions:
            self._activate()
        return self.transactions.get(thread.get_ident(), None)

    def __set__(self, inst, value):
        """Do nothing

        This used to issue a warning but it seems to be spurious.
        """
        pass

    @classmethod
    def install(cls, connectionURI, sqlClass=SQLBase, debug=False,
                implicitActivate=True, reconnect=False,
                isolation=DEFAULT_ISOLATION):
        if isinstance(sqlClass.__dict__.get('_connection'),
                _ZopelessConnectionDescriptor):
            # ZopelessTransactionManager.__new__ should now prevent this from
            # happening, so raise an error if it somehow does anyway.
            raise RuntimeError, "Already installed _connection descriptor."
        cls.sqlClass = sqlClass
        descriptor = cls(
                connectionURI, debug=debug, implicitActivate=implicitActivate,
                reconnect=reconnect, isolation=isolation
                )
        sqlClass._connection = descriptor
        return descriptor

    @classmethod
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

    # Reset database connection at end of every transaction?  We do this by
    # default to protect us against leaks and accidentally carrying over
    # state between logically unconnected requests, but sometimes we do need
    # to carry over state such as temporary tables.
    reset_after_transaction = True

    def __new__(cls, connectionURI, sqlClass=SQLBase, debug=False,
                implicitBegin=True, isolation=DEFAULT_ISOLATION):
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
                                        implicitBegin, isolation)
        return cls._installed

    def __init__(self, connectionURI, sqlClass=SQLBase, debug=False,
                 implicitBegin=True, isolation=DEFAULT_ISOLATION):
        # For some reason, Python insists on calling __init__ on anything
        # returned from __new__, even if it's not a newly constructed object
        # (i.e. type.__call__ calls __init__, rather than object.__new__ like
        # you'd expect).
        if self.alreadyInited:
            return
        self.alreadyInited = True

        # XXX: spiv 2004-10-25:
        #      Importing a module-global and assigning it as an instance
        #      attribute smells funny.  Why not just use transaction.manager
        #      instead of self.manager?
        from transaction import manager
        self.manager = manager
        desc = _ZopelessConnectionDescriptor.install(
            connectionURI, debug=debug, implicitActivate=implicitBegin,
            reconnect=not implicitBegin, isolation=isolation)
        self.sqlClass = sqlClass
        self.desc = desc
        # The next two instance variables are used for the check in __new__
        self.connectionURI = connectionURI
        self.debug = debug
        self.implicitBegin = implicitBegin
        if self.implicitBegin:
            self.begin()

    def set_isolation_level(self, level):
        """Set the transaction isolation level.

        Level can be one of AUTOCOMMIT_ISOLATION, READ_COMMITTED_ISOLATION
        or SERIALIZABLE_ISOLATION. As changing the isolation level must be
        done before any other queries are issued in the current transaction,
        this method automatically issues a rollback to ensure this is the
        case.
        """
        con = self.conn()
        # Changing the isolation level must be done before any other queries
        # in the transaction. To ensure this is the case, we rollback.
        con.rollback()
        con.set_isolation_level(level)
        # Make the isolation level stick
        self.desc.isolation = level
        cur = con.cursor()
        cur.execute('SHOW transaction_isolation')
        isolation_str = cur.fetchone()[0]
        if level == AUTOCOMMIT_ISOLATION:
            # psycopg implements autocommit using read committed and commits.
            assert isolation_str == 'read committed', 'Got ' + isolation_str
        elif level == READ_COMMITTED_ISOLATION:
            assert isolation_str == 'read committed', 'Got ' + isolation_str
        elif level == SERIALIZABLE_ISOLATION:
            assert isolation_str == 'serializable', 'Got ' + isolation_str
        else:
            raise AssertionError("Unknown transaction isolation level")

    def conn(self):
        return self.sqlClass._connection._connection

    def uninstall(self):
        _ZopelessConnectionDescriptor.uninstall()
        # We delete self.sqlClass to make sure this instance isn't still
        # used after uninstall was called, which is a little bit of a hack.
        self.manager.free(self.manager.get())
        del self.sqlClass
        self.__class__._installed = None

    def _dm(self):
        assert hasattr(self, 'sqlClass'), 'initZopeless not called'
        return self.sqlClass._connection._dm

    def begin(self):
        if not self.implicitBegin:
            self.desc._activate()
        clear_current_connection_cache()
        txn = self.manager.begin()
        txn.join(self._dm())
        self.set_isolation_level(self.desc.isolation)

    def commit(self):
        self.manager.get().commit()

        # By default we close the connection after completing a transaction,
        # to safeguard against cached SQLObject data and SQL session state
        # spilling out of their transactions.  Connection pooling keeps the
        # performance penalty acceptably low.
        if self.reset_after_transaction:
            self.desc._deactivate()

        if self.implicitBegin:
            self.begin()

    def abort(self):
        objects = list(self._dm().objects)
        self.manager.get().abort()
        for obj in objects:
            obj.reset()
            obj.expire()
        if self.reset_after_transaction:
            self.desc._deactivate()
        if self.implicitBegin:
            self.begin()


def clear_current_connection_cache():
    """Clear SQLObject's object cache for the current connection."""
    # XXX: Andrew Bennetts 2005-02-01:
    #      There is a different hack for (I think?) similar reasons in
    #      canonical.launchpad.webapp.publication.  This should probably
    #      share code with that one.

    # Don't break if _connection is a FakeZopelessConnectionDescriptor
    if getattr(SQLBase._connection, 'cache', None) is not None:
        for c in SQLBase._connection.cache.allSubCaches():
            c.clear()

def expire_from_cache(obj):
    """Expires a single object from the SQLObject cache."""
    if getattr(SQLBase._connection, 'cache', None) is not None:
        SQLBase._connection.cache.expire(obj.id, obj.__class__)


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

    Note that we need to receive a Unicode string back, because our
    query will be a Unicode string (the entire query will be encoded
    before sending across the wire to the database).

    >>> quote(u"\N{TRADE MARK SIGN}")
    u"'\u2122'"

    Timezone handling is not implemented, since all timestamps should
    be UTC anyway.

    >>> from datetime import datetime, date, time
    >>> quote(datetime(2003, 12, 4, 13, 45, 50))
    "'2003-12-04 13:45:50'"
    >>> quote(date(2003, 12, 4))
    "'2003-12-04'"
    >>> quote(time(13, 45, 50))
    "'13:45:50'"

    This function special cases datetime objects, due to a bug that has
    since been fixed in SQLOS (it installed an SQLObject converter that
    stripped the time component from the value).  By itself, the sqlrepr
    function has the following output:

    >>> sqlrepr(datetime(2003, 12, 4, 13, 45, 50), 'postgres')
    "'2003-12-04T13:45:50'"

    This function also special cases set objects, which SQLObject's
    sqlrepr() doesn't know how to handle.

    >>> quote(set([1,2,3]))
    '(1, 2, 3)'
    """
    if isinstance(x, datetime):
        return "'%s'" % x
    elif ISQLBase(x, None) is not None:
        return str(x.id)
    elif isinstance(x, set):
        # SQLObject can't cope with sets, so convert to a list, which it
        # /does/ know how to handle.
        x = list(x)
    return sqlrepr(x, 'postgres')

def quote_like(x):
    r"""Quote a variable ready for inclusion in a SQL statement's LIKE clause

    XXX: StuartBishop 2004-11-24:
    Including the single quotes was a stupid decision.

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
       % sqlvalues(BugTaskSeverity.CRITICAL, 'foo'))

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
    # XXX: Andrew Bennetts 2005-02-16 bug=452:
    # Turn that bug into a doctest
    for object in list(SQLBase._connection._dm.objects):
        object.syncUpdate()

def flush_database_caches():
    """Flush all cached values from the database for the current connection.

    SQLObject caches field values from the database in SQLObject
    instances.  If SQL statements are issued that change the state of
    the database behind SQLObject's back, these cached values will be
    invalid.

    This function iterates through all the objects in the SQLObject
    connection's cache, and synchronises them with the database.  This
    ensures that they all reflect the values in the database.
    """
    for cache in SQLBase._connection.cache.allSubCaches():
        # iterate over all the live objects
        for obj in cache.cache.values():
            try:
                obj.sync()
            except SQLObjectNotFound:
                obj.expire()
        # update all non-expired sqlobjects in the expiredCache dict.
        for value in cache.expiredCache.values():
            obj = value()
            if obj is None or obj._expired:
                continue
            try:
                obj.sync()
            except SQLObjectNotFound:
                obj.expire()


# Some helpers intended for use with initZopeless.  These allow you to avoid
# passing the transaction manager all through your code.
# XXX Andrew Bennetts 2005-02-11:
# Make these use and work with Zope 3's transaction machinery instead!

def begin():
    """Begins a transaction."""
    ZopelessTransactionManager._installed.begin()

def rollback():
    ZopelessTransactionManager._installed.abort()

def commit():
    ZopelessTransactionManager._installed.commit()

def connect(user, dbname=None, isolation=DEFAULT_ISOLATION):
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
    con = psycopg.connect(con_str)
    con.set_isolation_level(isolation)
    return con


def cursor():
    '''Return a cursor from the current database connection.

    This is useful for code that needs to issue database queries
    directly rather than using the SQLObject interface
    '''
    return SQLBase._connection._connection.cursor()


class FakeZopelessTransactionManager:
    # XXX Andrew Bennetts 2005-07-12:
    # There really should be a formal interface that both this and
    # ZopelessTransactionManager implement.

    def __init__(self, implicitBegin=False, isolation=DEFAULT_ISOLATION):
        assert ZopelessTransactionManager._installed is None
        ZopelessTransactionManager._installed = self
        self.desc = FakeZopelessConnectionDescriptor.install(None)
        self.implicitBegin = implicitBegin
        if self.implicitBegin:
            self.begin()

    @classmethod
    def install(cls):
        fztm = cls()
        ZopelessTransactionManager._installed = fztm
        FakeZopelessConnectionDescriptor.install(None)
        return fztm

    def uninstall(self):
        assert ZopelessTransactionManager._installed is self
        FakeZopelessConnectionDescriptor.uninstall()
        ZopelessTransactionManager._installed = None

    # XXX Andrew Bennetts 2005-07-12:
    #      Ideally I'd be able to re-use some of the ZopelessTransactionManager
    #      implementation of begin, commit and abort.
    def begin(self):
        if not self.implicitBegin:
            self.desc._activate()
        self.desc.begin()

    def commit(self, sub=False):
        self.desc.commit()
        self.desc._deactivate()
        if self.implicitBegin:
            self.begin()

    def abort(self, sub=False):
        self.desc.rollback()
        self.desc._deactivate()
        if self.implicitBegin:
            self.begin()


class FakeZopelessConnectionDescriptor(_ZopelessConnectionDescriptor):
    """A helper class for testing.

    Use this if you want to know if commit or rollback was called.
    """
    _obsolete = True
    activated = False
    begun = False
    rolledback = False
    committed = False

    def __get__(self, inst, cls=None):
        return self

    def _activate(self):
        assert not self.activated
        self.activated = True

    def _deactivate(self):
        assert self.activated
        self.activated = False

    def begin(self):
        assert self.activated
        self.begun = True

    def rollback(self):
        assert self.activated
        self.rolledback = True

    def commit(self):
        assert self.activated
        self.committed = True



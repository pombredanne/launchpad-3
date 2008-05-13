# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import thread
import warnings
import time
from datetime import datetime

import psycopg2
from psycopg2.extensions import (
    ISOLATION_LEVEL_AUTOCOMMIT, ISOLATION_LEVEL_READ_COMMITTED,
    ISOLATION_LEVEL_SERIALIZABLE)
import storm
from storm.databases.postgres import compile as postgres_compile
import storm.sqlobject
from storm.zope.interfaces import IZStorm
from sqlobject.sqlbuilder import sqlrepr

from zope.component import getUtility
from zope.interface import implements

from canonical.database.interfaces import ISQLBase

__all__ = [
    'alreadyInstalledMsg',
    'begin',
    'block_implicit_flushes',
    'clear_current_connection_cache',
    'commit',
    'ConflictingTransactionManagerError',
    'connect',
    'cursor',
    'expire_from_cache',
    'flush_database_caches',
    'flush_database_updates',
    'ISOLATION_LEVEL_AUTOCOMMIT',
    'ISOLATION_LEVEL_DEFAULT',
    'ISOLATION_LEVEL_READ_COMMITTED',
    'ISOLATION_LEVEL_SERIALIZABLE',
    'quote',
    'quote_like',
    'quoteIdentifier',
    'RandomiseOrderDescriptor',
    'rollback',
    'SQLBase',
    'sqlvalues',
    'ZopelessTransactionManager',]

# Default we want for scripts, and the PostgreSQL default. Note psycopg1 will
# use SERIALIZABLE unless we override, but psycopg2 will not.
ISOLATION_LEVEL_DEFAULT = ISOLATION_LEVEL_READ_COMMITTED


# XXX 20080313 jamesh:
# When quoting names in SQL statements, PostgreSQL treats them as case
# sensitive.  Storm includes a list of reserved words that it
# automatically quotes, which includes a few of our table names.  We
# remove them here due to case mismatches between the DB and Launchpad
# code.
postgres_compile.remove_reserved_words(['language', 'section'])


class LaunchpadStyle(storm.sqlobject.SQLObjectStyle):
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
    # AttributeError: 'LaunchpadStyle' object has no attribute
    # 'tableReference'
    def tableReference(self, table):
        """Return the tablename mapped for use in RelativeJoin statements."""
        return table.__str__()


class SQLBase(storm.sqlobject.SQLObjectBase):
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

    # Silence warnings in linter script, which complains about all
    # SQLBase-derived objects missing an id.
    id = None

    @staticmethod
    def _get_store():
        return getUtility(IZStorm).get('main')

    def __repr__(self):
        # XXX jamesh 2008-05-09:
        # This matches the repr() output for the sqlos.SQLOS class.
        # A number of the doctests rely on this formatting.
        return '<%s at 0x%x>' % (self.__class__.__name__, id(self))

    def reset(self):
        raise AssertionError("SQLBase.reset() not handled.")
        if not self._SO_createValues:
            return
        self._SO_writeLock.acquire()
        try:
            self.dirty = False
            self._SO_createValues = {}
        finally:
            self._SO_writeLock.release()


alreadyInstalledMsg = ("A ZopelessTransactionManager with these settings is "
"already installed.  This is probably caused by calling initZopeless twice.")


class ConflictingTransactionManagerError(Exception):
    pass


class ZopelessTransactionManager(object):
    """Compatibility shim for initZopeless()"""

    _installed = None
    _CONFIG_OVERLAY_NAME = 'initZopeless config overlay'

    def __init__(self):
        raise AssertionError("ZopelessTransactionManager should not be "
                             "directly instantiated.")

    @classmethod
    def initZopeless(cls, dbname=None, dbhost=None, dbuser=None,
                     isolation=ISOLATION_LEVEL_DEFAULT):
        # Construct a config fragment:
        overlay = '[database]\n'
        if dbname:
            overlay += 'dbname: %s\n' % dbname
        if dbhost:
            overlay += 'dbhost: %s\n' % dbhost
        overlay += 'isolation_level: %s\n' % {
            ISOLATION_LEVEL_AUTOCOMMIT: 'autocommit',
            ISOLATION_LEVEL_READ_COMMITTED: 'read_committed',
            ISOLATION_LEVEL_SERIALIZABLE: 'serializable'}[isolation]
        if dbuser:
            overlay += '\n[launchpad]\ndbuser: %s\n' % dbuser

        if cls._installed is not None:
            if cls._config_overlay != overlay:
                raise ConflictingTransactionManagerError(
                        "A ZopelessTransactionManager with different "
                        "settings is already installed")
            # There's an identical ZopelessTransactionManager already
            # installed, so return that one, but also emit a warning.
            warnings.warn(alreadyInstalledMsg, stacklevel=3)
        else:
            from canonical.config import config
            config.push(cls._CONFIG_OVERLAY_NAME, overlay)
            cls._config_overlay = overlay
            cls._reset_store()
            cls._installed = cls
        return cls._installed

    @staticmethod
    def _reset_store():
        """Reset the main store.

        This is required for connection setting changes to be made visible.
        """
        zstorm = getUtility(IZStorm)
        store = zstorm.get('main')
        zstorm.remove(store)
        store.close()

    @classmethod
    def uninstall(cls):
        """Uninstall the ZopelessTransactionManager.

        This entails removing the config overlay and 
        """
        assert cls._installed is not None, (
            "ZopelessTransactionManager not installed")
        from canonical.config import config
        config.pop(cls._CONFIG_OVERLAY_NAME)
        cls._reset_store()
        cls._installed = None

    @staticmethod
    def conn():
        store = getUtility(IZStorm).get("main")
        # Use of the raw connection will not be coherent with Storm's
        # cache.
        return store._connection._raw_connection

    @staticmethod
    def begin():
        """Begin a transaction."""
        transaction.begin()

    @staticmethod
    def commit():
        """Commit the current transaction."""
        transaction.commit()

    @staticmethod
    def abort():
        """Abort the current transaction."""
        transaction.abort()


def clear_current_connection_cache():
    """Clear SQLObject's object cache for the current connection."""
    getUtility(IZStorm).get('main').invalidate()

def expire_from_cache(obj):
    """Expires a single object from the SQLObject cache."""
    getUtility(IZStorm).get('main').invalidate(obj)


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
    getUtility(IZStorm).get('main').flush()

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
    getUtility(IZStorm).get('main').invalidate()


def block_implicit_flushes(func):
    """A decorator that blocks implicit flushes on the main store."""
    def wrapped(*args, **kwargs):
        store = getUtility(IZStorm).get("main")
        store.block_implicit_flushes()
        try:
            return func(*args, **kwargs)
        finally:
            store.unblock_implicit_flushes()
    wrapped.__name__ = func.__name__
    wrapped.__doc__ = func.__doc__
    return wrapped


# Some helpers intended for use with initZopeless.  These allow you to avoid
# passing the transaction manager all through your code.

def begin():
    """Begins a transaction."""
    transaction.begin()

def rollback():
    transaction.abort()

def commit():
    transaction.commit()

def connect(user, dbname=None, isolation=ISOLATION_LEVEL_DEFAULT):
    """Return a fresh DB-API connecction to the database.

    Use None for the user to connect as the default PostgreSQL user.
    This is not the default because the option should be rarely used.

    Default database name is the one specified in the main configuration file.
    """
    from canonical.config import config
    con_str = 'dbname=%s' % (dbname or config.database.dbname)
    if user:
        con_str += ' user=%s' % user
    if config.database.dbhost:
        con_str += ' host=%s' % config.database.dbhost
    con = psycopg2.connect(con_str)
    con.set_isolation_level(isolation)
    return con


def cursor():
    '''Return a cursor from the current database connection.

    This is useful for code that needs to issue database queries
    directly rather than using the SQLObject interface
    '''
    return getUtility(IZStorm).get('main')._connection.build_raw_cursor()


class FakeZopelessTransactionManager:
    # XXX Andrew Bennetts 2005-07-12:
    # There really should be a formal interface that both this and
    # ZopelessTransactionManager implement.

    def __init__(self, implicitBegin=False,
                 isolation=ISOLATION_LEVEL_DEFAULT):
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
    #      Ideally I'd be able to re-use some of the
    #      ZopelessTransactionManager implementation of begin, commit
    #      and abort.
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



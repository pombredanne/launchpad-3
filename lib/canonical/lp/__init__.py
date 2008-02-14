# Copyright 2004 Canonical Ltd.  All rights reserved.
# This module uses an older naming convention to support the callsites.
# pylint: disable-msg=C0103

"""Launcpad Zope extensions."""

__metaclass__ = type

import sys, os
from types import ClassType
from zope.interface.advice import addClassAdvisor
from zope.interface import classImplements

from canonical.database.sqlbase import (
        ZopelessTransactionManager, DEFAULT_ISOLATION)

import psycopgda.adapter


__all__ = [
    'DEFAULT_ISOLATION', 'AUTOCOMMIT_ISOLATION',
    'READ_COMMITTED_ISOLATION', 'SERIALIZABLE_ISOLATION',
    'dbname', 'dbhost', 'dbuser', 'isZopeless', 'initZopeless',
    'decorates', 'Passthrough',
    ]

# Allow override by environment variables for backwards compatibility.
# This was needed to allow tests to propogate settings to spawned processes.
# However, now we just have a single environment variable (LAUNCHPAD_CONF)
# which specifies which section of the config file to use instead,
# Note that an empty host is different to 'localhost', as the latter
# connects via TCP/IP instead of a Unix domain socket. Also note that
# if the host is empty it can be overridden by the standard PostgreSQL
# environment variables, this feature currently required by Async's
# office environment.


# Store the dbname, dbhost, and dbuser.
_db = {}

def _init_db():
    """Initialize the db values from the config."""
    if len(_db) == 0:
        import pdb; pdb.set_trace()
        # Avoid circular imports.
        from canonical.config import config
        _db['dbname'] = os.environ.get('LP_DBNAME', config.dbname)
        _db['dbhost'] = os.environ.get('LP_DBNAME', config.dbhost)
        _db['dbuser'] = os.environ.get('LP_DBUSER', config.launchpad.dbuser)


def create_db_property(key):
    """return a getter-setter property to access a db key."""
    def getter():
        """Return the key."""
        _init_db()
        return _db[key]

    def setter(value):
        """Set the key."""
        _db[key] = value

    return property(getter, setter, doc='Return the %s.' % key)


def dbname():
    """Return the dbname."""
    _init_db()
    return _db['dbname']

def _setdbname(value):
    """Set the dbname."""
    _db['dbname'] = value

dbname = property(dbname, _setdbname, doc=dbname.__doc__)


def dbhost():
    """Return the dbhost."""
    _init_db()
    return _db['dbhost']

def _setdbhost(value):
    """Set the dbhost."""
    _db['dbhost'] = value

dbhost = property(dbhost, _setdbhost, doc=dbhost.__doc__)


def dbuser():
    """Return the dbuser."""
    _init_db()
    return _db['dbuser']

def _setdbuser(value):
    """Set the dbhost."""
    _db['dbuser'] = value

dbuser = property(dbuser, _setdbuser, doc=dbuser.__doc__)


_typesRegistered = False
def registerTypes():
    '''Register custom type converters with psycopg

    After calling this method, string-type columns are returned as Unicode
    and date and time columns returned as Python datetime, date and time
    instances.

    To do this, we simply call the internal psycopg adapter method that
    does this. This is ugly, but ensures that the conversions work
    identically no matter if the Zope3 environment has been loaded. This
    is particularly important for the testing framework, as the converters
    are global and not reset in the test harness tear down methods.
    It also saves a lot of typing.

    This method is invoked on module load, ensuring that any code that
    needs to access the Launchpad database has the converters installed
    (since do do this you need to access dbname and dbhost from this module).

    We cannot unittest this method, but other tests will confirm that
    the converters are working as expected.

    '''
    global _typesRegistered
    if not _typesRegistered:
        psycopgda.adapter.registerTypes(psycopgda.adapter.PG_ENCODING)
        _typesRegistered = True

registerTypes()

def isZopeless():
    """Returns True if we are running in the Zopeless environment"""
    return ZopelessTransactionManager._installed is not None

def initZopeless(debug=False, dbname=None, dbhost=None, dbuser=None,
                 implicitBegin=True, isolation=DEFAULT_ISOLATION):
    registerTypes()
    if dbuser is None:
        # Nothing calling initZopeless should be connecting as the
        # 'launchpad' user, which is the default.
        # StuartBishop 20050923
        #warnings.warn(
        #        "Passing dbuser parameter to initZopeless will soon "
        #        "be mandatory", DeprecationWarning, stacklevel=2
        #        )
        pass # Disabled. Bug#3050
    if dbname is None:
        dbname = globals()['dbname']
    if dbhost is None:
        dbhost = globals()['dbhost']
    if dbuser is None:
        dbuser = globals()['dbuser']

    # If the user has been specified in the dbhost, it overrides.
    # Might want to remove this backwards compatibility feature at some
    # point.
    if '@' in dbhost or not dbuser:
        dbuser = ''
    else:
        dbuser = dbuser + '@'

    return ZopelessTransactionManager('postgres://%s%s/%s' % (
        dbuser, dbhost, dbname,
        ), debug=debug, implicitBegin=implicitBegin, isolation=isolation)

def decorates(interface, context='context'):
    """Make an adapter into a decorator.

    Use like:

      class RosettaProject:
          implements(IRosettaProject)
          decorates(IProject)

          def __init__(self, context):
              self.context = context

          def methodFromRosettaProject(self):
              return self.context.methodFromIProject()

    If you want to use a different name than "context" then you can explicitly
    say so:

      class RosettaProject:
          implements(IRosettaProject)
          decorates(IProject, context='project')

          def __init__(self, project):
              self.project = project

          def methodFromRosettaProject(self):
              return self.project.methodFromIProject()

    The adapter class will implement the interface it is decorating.

    The minimal decorator looks like this:

      class RosettaProject:
          decorates(IProject)

          def __init__(self, context):
              self.context = context

    """
    frame = sys._getframe(1)
    locals = frame.f_locals

    # Try to make sure we were called from a class def
    if (locals is frame.f_globals) or ('__module__' not in locals):
        raise TypeError("decorates can be used only from a class definition.")

    locals['__decorates_advice_data__'] = interface, context
    addClassAdvisor(_decorates_advice, depth=2)

def _decorates_advice(cls):
    interface, contextvar = cls.__dict__['__decorates_advice_data__']
    del cls.__decorates_advice_data__
    if type(cls) is ClassType:
        raise TypeError('cannot use decorates() on a classic class: %s' %
                        cls)
    classImplements(cls, interface)
    for name in interface:
        if not hasattr(cls, name):
            setattr(cls, name, Passthrough(name, contextvar))
    return cls

class Passthrough:

    def __init__(self, name, contextvar):
        self.name = name
        self.contextvar = contextvar

    def __get__(self, inst, cls=None):
        if inst is None:
            return self
        else:
            return getattr(getattr(inst, self.contextvar), self.name)

    def __set__(self, inst, value):
        setattr(getattr(inst, self.contextvar), self.name, value)

    def __delete__(self, inst):
        raise NotImplementedError


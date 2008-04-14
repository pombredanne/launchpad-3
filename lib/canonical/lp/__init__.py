# Copyright 2004 Canonical Ltd.  All rights reserved.

"""This module provides the Zopeless PG environment.

This module is deprecated.
"""

# This module uses a different naming convention to support the callsites.
# pylint: disable-msg=C0103

__metaclass__ = type

import os

from canonical.config import config
from canonical.database.sqlbase import (
    ISOLATION_LEVEL_DEFAULT, ZopelessTransactionManager)


__all__ = [
    'dbname', 'dbhost', 'dbuser', 'isZopeless', 'initZopeless',
    ]

# Allow override by environment variables for backwards compatibility.
# This was needed to allow tests to propagate settings to spawned processes.
# However, now we just have a single environment variable (LAUNCHPAD_CONF)
# which specifies which section of the config file to use instead,
# Note that an empty host is different to 'localhost', as the latter
# connects via TCP/IP instead of a Unix domain socket. Also note that
# if the host is empty it can be overridden by the standard PostgreSQL
# environment variables, this feature currently required by Async's
# office environment.
dbname = os.environ.get('LP_DBNAME', config.database.dbname)
dbhost = os.environ.get('LP_DBHOST', config.database.dbhost or '')
dbuser = os.environ.get('LP_DBUSER', config.launchpad.dbuser)


def isZopeless():
    """Returns True if we are running in the Zopeless environment"""
    # pylint: disable-msg=W0212
    return ZopelessTransactionManager._installed is not None


def initZopeless(debug=False, dbname=None, dbhost=None, dbuser=None,
                 implicitBegin=True, isolation=ISOLATION_LEVEL_DEFAULT):
    """Initialize the Zopeless environment."""
    if dbuser is None:
        # Nothing calling initZopeless should be connecting as the
        # 'launchpad' user, which is the default.
        # StuartBishop 20050923
        # warnings.warn(
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


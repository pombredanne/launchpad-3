# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""This module provides the Zopeless PG environment.

This module is deprecated.
"""

# This module uses a different naming convention to support the callsites.
# pylint: disable-msg=C0103

__metaclass__ = type

import os

from canonical.database.postgresql import ConnectionString
from canonical.config import dbconfig
from canonical.database.sqlbase import (
    ISOLATION_LEVEL_DEFAULT, ZopelessTransactionManager)


__all__ = [
    'get_dbname', 'dbhost', 'dbuser', 'isZopeless', 'initZopeless',
    ]

# SQLObject compatibility - dbname, dbhost and dbuser are DEPRECATED.
#
# Allow override by environment variables for backwards compatibility.
# This was needed to allow tests to propagate settings to spawned processes.
# However, now we just have a single environment variable (LAUNCHPAD_CONF)
# which specifies which section of the config file to use instead,
# Note that an empty host is different to 'localhost', as the latter
# connects via TCP/IP instead of a Unix domain socket. Also note that
# if the host is empty it can be overridden by the standard PostgreSQL
# environment variables, this feature currently required by Async's
# office environment.
dbhost = os.environ.get('LP_DBHOST', None)
dbuser = os.environ.get('LP_DBUSER', None)
dbport = os.environ.get('LP_DBPORT', None)
dbname_override = os.environ.get('LP_DBNAME', None)


def get_dbname():
    """Get the DB Name for scripts: deprecated.

    :return: The dbname for scripts.
    """
    if dbname_override is not None:
        return dbname_override
    dbname = ConnectionString(dbconfig.main_master).dbname
    assert dbname is not None, 'Invalid main_master connection string'
    return  dbname


if dbhost is None:
    dbhost = ConnectionString(dbconfig.main_master).host
if dbport is None:
    dbport = ConnectionString(dbconfig.main_master).port

if dbuser is None:
    dbuser = dbconfig.dbuser


def isZopeless():
    """Returns True if we are running in the Zopeless environment"""
    # pylint: disable-msg=W0212
    return ZopelessTransactionManager._installed is not None


_IGNORED = object()


def initZopeless(dbname=None, dbhost=None, dbuser=None,
                 isolation=ISOLATION_LEVEL_DEFAULT):
    """Initialize the Zopeless environment."""
    if dbuser is None:
        # Nothing calling initZopeless should be connecting as the
        # 'launchpad' user, which is the default.
        # StuartBishop 20050923
        # warnings.warn(
        #        "Passing dbuser parameter to initZopeless will soon "
        #        "be mandatory", DeprecationWarning, stacklevel=2
        #        )
        pass  # Disabled. Bug #3050
    if dbname is None:
        dbname = get_dbname()
    if dbhost is None:
        dbhost = globals()['dbhost']
    if dbuser is None:
        dbuser = globals()['dbuser']

    return ZopelessTransactionManager.initZopeless(
        dbname=dbname, dbhost=dbhost, dbuser=dbuser, isolation=isolation)

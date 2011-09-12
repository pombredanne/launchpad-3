# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""This module provides the Zopeless PG environment.

This module is deprecated.
"""

# This module uses a different naming convention to support the callsites.
# pylint: disable-msg=C0103

__metaclass__ = type

from canonical.database.postgresql import ConnectionString
from canonical.config import dbconfig
from canonical.database.sqlbase import (
    ISOLATION_LEVEL_DEFAULT, ZopelessTransactionManager)


__all__ = [
    'isZopeless', 'initZopeless',
    ]


def isZopeless():
    """Returns True if we are running in the Zopeless environment"""
    # pylint: disable-msg=W0212
    return ZopelessTransactionManager._installed is not None


def initZopeless(dbname=None, dbhost=None, dbuser=None,
                 isolation=ISOLATION_LEVEL_DEFAULT):
    """Initialize the Zopeless environment."""
    if dbuser is None:
        dbuser = (
            ConnectionString(dbconfig.main_master).user or dbconfig.dbuser)

    return ZopelessTransactionManager.initZopeless(
        dbname=dbname, dbhost=dbhost, dbuser=dbuser, isolation=isolation)

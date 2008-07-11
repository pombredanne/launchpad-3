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
    'isZopeless', 'initZopeless',
    ]


def isZopeless():
    """Returns True if we are running in the Zopeless environment"""
    # pylint: disable-msg=W0212
    return ZopelessTransactionManager._installed is not None


_IGNORED = object()


def initZopeless(debug=_IGNORED, dbname=None, dbhost=None, dbuser=None,
                 implicitBegin=_IGNORED, isolation=ISOLATION_LEVEL_DEFAULT):
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

    return ZopelessTransactionManager.initZopeless(
        dbname=dbname, dbhost=dbhost, dbuser=dbuser, isolation=isolation)

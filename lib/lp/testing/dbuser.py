# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Provides a context manager to run parts of a test as a different dbuser."""

__metaclass__ = type
__all__ = [
    'dbuser',
    'lp_dbuser',
    ]

from contextlib import contextmanager

import transaction

from canonical.config import dbconfig
from canonical.database.sqlbase import update_store_connections


@contextmanager
def dbuser(temporary_name):
    """A context manager that temporarily changes the dbuser.

    Use with the LaunchpadZopelessLayer layer and subclasses.

    temporary_name is the name of the dbuser that should be in place for the
    code in the "with" block.
    """
    transaction.commit()
    old_name = getattr(dbconfig.overrides, 'dbuser', None)
    dbconfig.override(dbuser=temporary_name)
    update_store_connections()
    yield
    transaction.commit()
    dbconfig.override(dbuser=old_name)
    update_store_connections()


def lp_dbuser():
    """A context manager that temporarily changes to the launchpad dbuser.

    Use with the LaunchpadZopelessLayer layer and subclasses.
    """
    return dbuser('launchpad')

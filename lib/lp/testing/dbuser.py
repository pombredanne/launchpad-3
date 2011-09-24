# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Provides a context manager to run parts of a test as a different dbuser."""

__metaclass__ = type
__all__ = [
    'dbuser',
    'lp_dbuser',
    'switch_dbuser',
    ]

from contextlib import contextmanager

import transaction

from canonical.config import dbconfig
from canonical.database.sqlbase import update_store_connections


def switch_dbuser(new_name):
    """Change the current database user.

    If new_name is None, the default will be restored.
    """
    transaction.commit()
    dbconfig.override(dbuser=new_name)
    update_store_connections()


@contextmanager
def dbuser(temporary_name):
    """A context manager that temporarily changes the dbuser.

    Use with the LaunchpadZopelessLayer layer and subclasses.

    temporary_name is the name of the dbuser that should be in place for the
    code in the "with" block.
    """
    old_name = getattr(dbconfig.overrides, 'dbuser', None)
    switch_dbuser(temporary_name)
    yield
    switch_dbuser(old_name)


def lp_dbuser():
    """A context manager that temporarily changes to the launchpad dbuser.

    Use with the LaunchpadZopelessLayer layer and subclasses.
    """
    return dbuser('launchpad')

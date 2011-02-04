# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Provides a context manager to run parts of a test as a different dbuser."""

__metaclass__ = type
__all__ = [
    'dbuser',
    'lp_dbuser',
    ]

from contextlib import contextmanager

from canonical.database.sqlbase import commit
from canonical.testing.layers import LaunchpadZopelessLayer

@contextmanager
def dbuser(temporary_name, restore_name=None):
    """A context manager that temporarily changes the dbuser.
    
    Use with the LaunchpadZopelessLayer layer and subclasses.
    
    temporary_name is the name of the dbuser that should be in place for the
    code in the "with" block.  restore_name is the name of the dbuser that
    should be restored after the with block.  If it is not supplied, the
    dbuser currently set (as far as LaunchpadZopelessLayer knows) is used.
    """
    if restore_name is None:
        restore_name = LaunchpadZopelessLayer.txn._dbuser
    commit()
    # Note that this will raise an assertion error if the
    # LaunchpadZopelessLayer is not already set up.
    LaunchpadZopelessLayer.switchDbUser(temporary_name)
    yield
    commit()
    LaunchpadZopelessLayer.switchDbUser(restore_name)

def lp_dbuser(restore_name=None):
    """A context manager that temporarily changes to the launchpad dbuser.
    
    Use with the LaunchpadZopelessLayer layer and subclasses.
    
    restore_name is the name of the dbuser that should be restored after
    the with block.  If it is not supplied, the dbuser currently set (as
    far as LaunchpadZopelessLayer knows) is used.
    """
    return dbuser('launchpad', restore_name=restore_name)

# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Script run from test_isolation.py to confirm transaction isolation
settings work. Note we need to use a non-default isolation level to
confirm that the changes are actually being made by the API calls."""

__metaclass__ = type
__all__ = []

from canonical.database.sqlbase import cursor, ISOLATION_LEVEL_SERIALIZABLE
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.lp import initZopeless

execute_zcml_for_scripts()

def check():
    cur = cursor()
    cur.execute("UPDATE Person SET country=61 WHERE name='sabdfl'")
    cur.execute("SHOW transaction_isolation")
    print cur.fetchone()[0]

    txn.abort()
    txn.begin()

    cur = cursor()
    cur.execute("UPDATE Person SET country=66 WHERE name='sabdfl'")
    cur.execute("SHOW transaction_isolation")
    print cur.fetchone()[0]

# First confirm the default isolation level
txn = initZopeless()
check()
txn.uninstall()

# We run the checks twice to ensure that both methods of setting the
# isolation level stick across transaction boundaries.
txn = initZopeless(isolation=ISOLATION_LEVEL_SERIALIZABLE)
check()
txn.uninstall()

txn = initZopeless()
txn.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)
check()


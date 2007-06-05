# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Script run from test_isolation.py to confirm transaction isolation
settings work."""

__metaclass__ = type
__all__ = []

from canonical.database.sqlbase import READ_COMMITTED_ISOLATION, cursor
from canonical.lp import initZopeless
from canonical.launchpad.scripts import execute_zcml_for_scripts

execute_zcml_for_scripts()

def check():
    cur = cursor()
    cur.execute("UPDATE Person SET password='bar' WHERE name='sabdfl'")
    cur.execute("SHOW transaction_isolation")
    print cur.fetchone()[0]

    txn.abort()
    txn.begin()

    cur = cursor()
    cur.execute("UPDATE Person SET password='baz' WHERE name='sabdfl'")
    cur.execute("SHOW transaction_isolation")
    print cur.fetchone()[0]

# We run the checks twice to ensure that both methods of setting the
# isolation level stick across transaction boundaries.
txn = initZopeless(isolation=READ_COMMITTED_ISOLATION)
check()
txn.uninstall()

txn = initZopeless()
txn.set_isolation_level(READ_COMMITTED_ISOLATION)
check()


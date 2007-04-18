# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Script run from test_isolation.py to confirm transaction isolation
settings work."""

__metaclass__ = type
__all__ = []

from canonical.database.sqlbase import READ_COMMITTED_ISOLATION, cursor
from canonical.lp import initZopeless
from canonical.launchpad.scripts import execute_zcml_for_scripts

execute_zcml_for_scripts()

txn = initZopeless(isolation=READ_COMMITTED_ISOLATION)
cur = cursor()
cur.execute("SHOW transaction_isolation")
print cur.fetchone()[0]

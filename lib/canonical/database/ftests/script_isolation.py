# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Script run from test_isolation.py to confirm transaction isolation
settings work. Note we need to use a non-default isolation level to
confirm that the changes are actually being made by the API calls."""

__metaclass__ = type
__all__ = []

import warnings

# XXX: 2010-04-26, Salgado, bug=570246: Silence python2.6 deprecation
# warnings.
warnings.filterwarnings(
    'ignore', '.*(md5|sha|sets)', DeprecationWarning,
    )

from canonical.database.sqlbase import cursor, ISOLATION_LEVEL_SERIALIZABLE
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.lp import initZopeless

execute_zcml_for_scripts()

def check():
    cur = cursor()
    cur.execute("UPDATE Person SET homepage_content='foo' WHERE name='mark'")
    cur.execute("SHOW transaction_isolation")
    print cur.fetchone()[0]

    txn.abort()
    txn.begin()

    cur = cursor()
    cur.execute("UPDATE Person SET homepage_content='bar' WHERE name='mark'")
    cur.execute("SHOW transaction_isolation")
    print cur.fetchone()[0]

# First confirm the default isolation level
txn = initZopeless()
check()
txn.uninstall()

txn = initZopeless(isolation=ISOLATION_LEVEL_SERIALIZABLE)
check()
txn.uninstall()

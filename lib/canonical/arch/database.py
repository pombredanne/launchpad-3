# arch-tag: 0b969817-f8a9-4a99-bb02-b4b2e749845b
#
# Copyright (C) 2004 Canonical Software
# 	Authors: Rob Weir <rob.weir@canonical.com>
#		 Robert Collins <robert.collins@canonical.com>

# higher-level callers are responsible for splitting these into transactions.

from canonical.database.sqlbase import quote, SQLBase
from canonical.launchpad.database import * # FIXME: backwards compat

import warnings

def dbname():
    return 'dbname=launchpad_test'

DBHandle = None

def connect():
    global DBHandle
    from sqlobject import connectionForURI
    from canonical.database.sqlbase import SQLBase
    conn = connectionForURI('postgres:///launchpad_test')
    SQLBase.initZopeless(conn)
    DBHandle = conn.getConnection()

#connect()

def nuke():
    if not DBHandle:
        connect()
    cursor = DBHandle.cursor()
    cursor.execute("DELETE FROM ChangesetFileHash")    
    cursor.execute("DELETE FROM ChangesetFile")
    cursor.execute("DELETE FROM ChangesetFileName")
    cursor.execute("DELETE FROM Changeset")
    cursor.execute("DELETE FROM Branch")
    cursor.execute("DELETE FROM ArchNamespace")
    cursor.execute("DELETE FROM ArchArchiveLocation")
    cursor.execute("DELETE FROM ArchArchive")
    commit()

def commit():
    DBHandle.commit()


#!/usr/bin/env python
"""
dropdb only more so.

Cut off access, slaughter connections and burn the database to the ground.
"""

import os
import sys
import time
import psycopg
from signal import SIGINT, SIGTERM, SIGKILL

if len(sys.argv) != 2:
    print >> sys.stderr, 'Must specify one, and only one, database to destroy'
    sys.exit(1)

database = sys.argv[1]

if database in ('template1', 'template0'):
    print >> sys.stderr, "Put the gun down and back away from the vehicle!"
    sys.exit(666)

if os.environ['USER'] != 'postgres':
    print >> sys.stderr, "You are not worthy. User postgres only."
    sys.exit(7)

con = psycopg.connect("dbname=template1 user=postgres")

# Set the transaction isolation level to allow us to do
# transaction-incompatible commands like 'drop database'
con.set_isolation_level(0)

cur = con.cursor()

# Ensure the database exists. Note that the script returns success
# in this case to ease scripting.
cur.execute("SELECT count(*) FROM pg_database WHERE datname=%s", [database])
if cur.fetchone()[0] == 0:
    print >> sys.stderr, \
            "%s has fled the building. Database does not exist" % database
    sys.exit(0)

# Stop connetions to the doomed database
cur.execute(
        "UPDATE pg_database SET datallowconn=false WHERE datname=%s",
        [database]
        )

# Shoot connections and slaughter the survivors
for signal in [SIGINT, SIGTERM, SIGKILL]:
    cur.execute(
            "SELECT procpid FROM pg_stat_activity WHERE datname=%s", [database]
            )
    pids = list(cur.fetchall())
    for (pid,) in pids:
        os.kill(pid, signal)
    if len(pids) > 0:
	time.sleep(5)

# Destroy the database

cur.execute("DROP DATABASE %s" % database) # Not quoted

# print "Mwahahahaha!"


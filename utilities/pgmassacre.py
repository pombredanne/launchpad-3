#!/usr/bin/python2.4
"""
dropdb only more so.

Cut off access, slaughter connections and burn the database to the ground.
"""

import os
import sys
import time
import psycopg
from signal import SIGTERM, SIGQUIT, SIGKILL, SIGINT
from optparse import OptionParser


def connect():
    if options.user is not None:
        return psycopg.connect("dbname=template1 user=%s" % options.user)
    else:
        return psycopg.connect("dbname=template1")


def send_signal(database, signal):
    con = connect()
    con.set_isolation_level(1)
    cur = con.cursor()

    # Install PL/PythonU if it isn't already
    cur.execute("SELECT TRUE FROM pg_language WHERE lanname = 'plpythonu'")
    if cur.fetchone() is None:
        cur.execute('CREATE LANGUAGE "plpythonu"')

    # Create a stored procedure to kill a backend process
    qdatabase = str(psycopg.QuotedString(database))
    cur.execute("""
        CREATE OR REPLACE FUNCTION _pgmassacre_killall(integer)
        RETURNS Boolean AS $$
        import os

        signal = args[0]
        for row in plpy.execute('''
            SELECT procpid FROM pg_stat_activity WHERE datname=%(qdatabase)s
                AND procpid != pg_backend_pid()
            '''):
            try:
                os.kill(row['procpid'], signal)
            except OSError:
                pass
        else:
            return False

        return True
        $$ LANGUAGE plpythonu
        """ % vars())

    cur.execute("SELECT _pgmassacre_killall(%(signal)s)", vars())
    con.rollback()
    con.close()


def still_open(database):
    """Return True if there are still open connections. Waits a while
    to ensure that connections shutting down have a chance to.
    """
    con = connect()
    con.set_isolation_level(1)
    cur = con.cursor()
    # Wait for up to 10 seconds, returning True if all backends are gone.
    start = time.time()
    while time.time() < start + 10:
        cur.execute("""
            SELECT procpid FROM pg_stat_activity
            WHERE datname=%(database)s LIMIT 1
            """, vars())
        if cur.fetchone() is None:
            return False
        time.sleep(0.6) # Stats only updated every 500ms
    con.rollback()
    con.close()
    return True

options = None

def main():
    parser = OptionParser()
    parser.add_option("-U", "--user", dest="user", default=None,
            help="Connect as USER", metavar="USER",
            )
    global options
    (options, args) = parser.parse_args()

    if len(args) != 1:
        print >> sys.stderr, \
                'Must specify one, and only one, database to destroy'
        sys.exit(1)

    database = args[0]

    if database in ('template1', 'template0'):
        print >> sys.stderr, "Put the gun down and back away from the vehicle!"
        return 666

    con = connect()

    cur = con.cursor()

    # Ensure the database exists. Note that the script returns success
    # if the database does not exist to ease scripting.
    cur.execute("SELECT count(*) FROM pg_database WHERE datname=%s", [database])
    if cur.fetchone()[0] == 0:
        print >> sys.stderr, \
                "%s has fled the building. Database does not exist" % database
        return 0

    # Stop connetions to the doomed database
    cur.execute(
        "UPDATE pg_database SET datallowconn=false WHERE datname=%s", [database]
        )

    con.commit()
    con.close()

    # Terminate current statements
    send_signal(database, SIGINT)

    # Shutdown current connections normally
    send_signal(database, SIGTERM)

    # Shutdown current connections immediately
    if still_open(database):
        send_signal(database, SIGQUIT)

    # Shutdown current connections nastily
    if still_open(database):
        send_signal(database, SIGKILL)

    if still_open(database):
        print >> sys.stderr, \
                "Unable to kill all backends! Database not destroyed."
        return 9

    # Destroy the database
    con = connect()
    con.set_isolation_level(0) # Required to execute commands like DROP DATABASE
    cur = con.cursor()
    cur.execute("DROP DATABASE %s" % database) # Not quoted
    return 0

    # print "Mwahahahaha!"

if __name__ == '__main__':
    sys.exit(main())

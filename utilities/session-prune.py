#!/usr/bin/python2.4

import psycopg
import sys
import traceback
import time

print 'Opening connection to %s' % sys.argv[1]
con = psycopg.connect('dbname=%s' % sys.argv[1])
con.set_isolation_level(0)
cur = con.cursor()

def create_used_sessions(cur):
    print 'Creating UsedSessions temporary table...'

    cur.execute("""
    CREATE TEMPORARY TABLE UsedSessions AS
    SELECT client_id FROM SessionPkgData
    WHERE product_id='launchpad.authenticateduser' AND key='logintime'
    UNION
    SELECT client_id FROM SessionData
    WHERE last_accessed >= CURRENT_TIMESTAMP - '1 day'::interval
    EXCEPT
    SELECT client_id FROM SessionData
    WHERE last_accessed < CURRENT_TIMESTAMP - '60 days'::interval
    """)

    cur.execute("""SELECT COUNT(*) FROM UsedSessions""")
    used_sessions = cur.fetchone()[0]
    cur.execute("""SELECT COUNT(*) FROM SessionData""")
    all_sessions = cur.fetchone()[0]
    print "%d of %d" % (used_sessions, all_sessions)

    print 'Indexing UsedSessions'
    cur.execute("""
    CREATE UNIQUE INDEX usedsessions__client_id__idx ON UsedSessions(client_id)
    """)

    print 'Analyzing UsedSessions'
    cur.execute("""ANALYZE UsedSessions""")

print 'Getting oldest session access time...',
cur.execute("""
    SELECT (extract(epoch FROM CURRENT_TIMESTAMP)
        - extract(epoch FROM min(last_accessed)))/(60*60) FROM SessionData
    """)
#oldest_access_in_hours = int(cur.fetchone()[0])
oldest_access_in_hours = 60*24
print '%f days' % (oldest_access_in_hours / 24.0,)

step_mins = 15 # We trash this many minutes worth of session data each query

one_day_in_mins = 24*60

now = 0

for minutes in range(
        oldest_access_in_hours * 60 + step_mins, one_day_in_mins, -step_mins
        ):
    while True:
        try:
            if time.time() > now + 60*60:
                print 'Rebuilding UsedSessions'
                if now != 0:
                    cur.execute("DROP TABLE UsedSessions")
                create_used_sessions(cur)
                now = time.time()
            print 'Trashing unused sessions older than',
            print '%d mins (%0.3f days)...' % (
                    minutes, minutes / (60.0*24.0)
                    ),
            until_mins = minutes
            from_mins = minutes - step_mins
            query = """
                DELETE FROM SessionData WHERE (
                    last_accessed BETWEEN CURRENT_TIMESTAMP
                        - '%(from_mins)d minutes'::interval AND
                        CURRENT_TIMESTAMP - '%(until_mins)d minutes'::interval
                    )
                    AND NOT EXISTS (
                        SELECT TRUE FROM UsedSessions
                        WHERE UsedSessions.client_id = SessionData.client_id
                        )
                """ % vars()
            cur.execute(query)
            break
        except psycopg.Error:
            print 'oops'
            traceback.print_exc()
            time.sleep(1)
    print '%d nuked.' % (cur.rowcount,)


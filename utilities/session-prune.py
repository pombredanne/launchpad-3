#!/usr/bin/python2.4

import psycopg
import sys
import traceback
import time

SHOW_STATS = True

print 'Opening connection to %s' % sys.argv[1]
con = psycopg.connect('dbname=%s' % sys.argv[1])
con.set_isolation_level(0)
cur = con.cursor()

print 'Getting oldest session access time...',
cur.execute("""
    SELECT (extract(epoch FROM CURRENT_TIMESTAMP)
        - extract(epoch FROM min(last_accessed)))/(60*60) FROM SessionData
    """)
try:
    oldest_access_in_hours = int(cur.fetchone()[0])
except TypeError:
    oldest_access_in_hours = 60*24
print '%f days' % (oldest_access_in_hours / 24.0,)

step_mins = 60 # We trash this many minutes worth of session data each query

one_day_in_mins = 24*60

now = 0

for minutes in range(
        oldest_access_in_hours * 60 + step_mins, one_day_in_mins, -step_mins
        ):
    while True:
        try:
            print 'Trashing unused sessions older than',
            print '%d mins (%0.3f days)...' % (
                    minutes, minutes / (60.0*24.0)
                    ),
            until_mins = minutes
            from_mins = minutes + step_mins + max(step_mins/4,1)
            if SHOW_STATS:
                query = """
                    SELECT COUNT(*) FROM SessionData
                    WHERE
                        last_accessed BETWEEN
                            CURRENT_TIMESTAMP - '%(from_mins)d minutes'::interval
                            AND CURRENT_TIMESTAMP
                                    - '%(until_mins)d minutes'::interval
                    """ % vars()
                cur.execute(query)
                total = cur.fetchone()[0]
            else:
                total = '??'
            query = """
                DELETE FROM SessionData
                WHERE
                    last_accessed BETWEEN
                        CURRENT_TIMESTAMP - '%(from_mins)d minutes'::interval
                        AND CURRENT_TIMESTAMP
                                - '%(until_mins)d minutes'::interval
                    AND client_id NOT IN (
                        SELECT SD.client_id
                        FROM SessionData AS SD,SessionPkgData
                        WHERE SessionPkgData.client_id = SD.client_id
                            AND product_id='launchpad.authenticateduser'
                            AND key='logintime'
                            AND SD.last_accessed BETWEEN
                                CURRENT_TIMESTAMP
                                    - '%(from_mins)d minutes'::interval
                                AND CURRENT_TIMESTAMP
                                    - '%(until_mins)d minutes'::interval
                        )
                """ % vars()
            cur.execute(query)
            print '%d/%s nuked.' % (cur.rowcount, total)
            break
        except psycopg.Error:
            print 'oops'
            traceback.print_exc()
            time.sleep(1)


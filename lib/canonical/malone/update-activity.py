#!/usr/bin/env python
# arch-tag: E33F5B5E-ED25-11D8-B59B-000D9329A36C

"""Updates activity score

Factor in:
- creation date
- last modified
- how many activity entries (last 7 days)
- total activity of bug (how many, how recent)
- duplicates (how many, how recent)
- number of unique commenters
- hit score
"""

from datetime import datetime
import psycopg
conn = psycopg.connect('dbname=launchpad_test user=andrew')
curs = conn.cursor()
curs.execute('SELECT id, hits FROM Bug')
for id, hits in curs.fetchall():
    score = hits

    # Amount of activity
    curs.execute('SELECT COUNT(*) FROM BugMessage WHERE bug=%d' % id)
    score += curs.fetchone()[0]

    # Number of duplicates
    curs.execute('SELECT COUNT(*) FROM Bug WHERE duplicateof=%d' % id)
    score += curs.fetchone()[0]

    # Number of unique commenters
    curs.execute('SELECT COUNT(DISTINCT personmsg) FROM BugMessage '
                 'WHERE bug=%d' % id)
    score += curs.fetchone()[0]

    curs.execute('UPDATE Bug SET activityscore=%d, activitytimestamp=now() '
                 'WHERE id=%d' % (score, id))
conn.commit()

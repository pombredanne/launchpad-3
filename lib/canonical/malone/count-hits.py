#!/usr/bin/env python
# arch-tag: 0C8E0435-E79C-11D8-B39C-000D9329A36C

"""Counts hits on bugs and updates hit counter in database.

Examines the local Z2.log file for hits on bugs and updates the hit counter.
Designed to be called from a cron job.
"""

import re
from time import strptime
# SQLObject 0.5.2 does not support the MAX() aggregator so we need to use
# psychopg directly. Has been discussed on the mail list so support will
# probably be added in the future.
import psycopg

# These two lines will need to be edited
z2 = file('/Users/andrew/src/Launchpad/launchpad/launchpad-access.log')
conn = psycopg.connect('dbname=launchpad user=andrew')

curs = conn.cursor()
curs.execute('SELECT MAX(hitstimestamp) FROM Bug')
lastupdate = curs.fetchone()[0]
target_url = re.compile(r'/malone/bugs/\d+$')

for line in z2:
    parts = line.split(' ')
    hitdate = strptime(parts[3][1:], '%d/%b/%Y:%H:%M:%S')
    if hitdate <= lastupdate or not target_url.search(parts[6]):
        continue
    id = parts[6].split('/')[-1]
    query = 'UPDATE Bug SET hits=hits+1, hitstimestamp=now() WHERE id=%s' % id
    curs.execute(query)

conn.commit()

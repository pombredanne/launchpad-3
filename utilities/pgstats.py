#!/usr/bin/env python
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""
Generate some statistics about a PostgreSQL database suitable for
emailing via cron
"""

__metaclass__ = type

import sys
import psycopg

def percentage(num, total):
    """Return a percentage string of num/total"""
    if total == 0:
        return 'Unknown'
    else:
        return '%3.2f%%' % ( (num * 100.0) / total, )


def print_row(key, value):
    print '%(key)-20s: %(value)s' % vars()


def main(dbname):
    con = psycopg.connect("dbname=%s" % dbname)
    cur = con.cursor()

    print 'Statistics for %s' % dbname
    print '===============' + '=' * (len(dbname))

    # Database level statistics
    cur.execute("""
        SELECT blks_hit, blks_read, numbackends,xact_commit, xact_rollback
            FROM pg_stat_database
            WHERE datname=%(dbname)s
        """, vars())
    hit, read, backends, commits, rollbacks = cur.fetchone()

    hit_rate = percentage(hit, hit + read)

    print_row("Cache hit rate", hit_rate)
    print_row("Number of backends", backends)

    commit_rate = percentage(commits, commits + rollbacks)

    print_row("Commit rate", commit_rate)

    # Unused indexes, ignoring primary keys.
    # TODO: We should identify constraints used to enforce uniqueness too
    cur.execute("""
        SELECT relname, indexrelname
            FROM pg_stat_user_indexes AS u JOIN pg_indexes AS i
                ON u.schemaname = i.schemaname
                    AND u.relname = i.tablename
                    AND u.indexrelname = i.indexname
            WHERE
                idx_scan = 0
                AND indexrelname NOT LIKE '%_pkey'
                AND indexdef NOT LIKE 'CREATE UNIQUE %'
        """)

    rows = cur.fetchall()
    if len(rows) == 0:
        print_row('Unused indexes', 'N/A')
    else:
        print_row('Unused indexes', rows[0][1])
        for table, index in rows[1:]:
            print_row('', index)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print >> sys.stderr, "Usage: %s [DBNAME]" % sys.argv[0]
        sys.exit(1)
    dbname = sys.argv[1]
    main(dbname)

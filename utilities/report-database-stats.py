#!/usr/bin/python2.5 -S
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Generate the database statistics report."""

__metaclass__ = type

import _pythonpath

from operator import attrgetter

from canonical.database.sqlbase import connect, sqlvalues
from canonical.launchpad.scripts import db_options
from lp.scripts.helpers import LPOptionParser


class Table:
    pass


def get_table_stats(cur, options):
    tablestats_query = """
        SELECT
            Earliest.date_created AS date_start,
            Latest.date_created AS date_end,
            Latest.schemaname,
            Latest.relname,
            Latest.seq_scan - Earliest.seq_scan AS seq_scan,
            Latest.seq_tup_read - Earliest.seq_tup_read AS seq_tup_read,
            Latest.idx_scan - Earliest.idx_scan AS idx_scan,
            Latest.idx_tup_fetch - Earliest.idx_tup_fetch AS idx_tup_fetch,
            Latest.n_tup_ins - Earliest.n_tup_ins AS n_tup_ins,
            Latest.n_tup_upd - Earliest.n_tup_upd AS n_tup_upd,
            Latest.n_tup_del - Earliest.n_tup_del AS n_tup_del,
            Latest.n_tup_hot_upd - Earliest.n_tup_hot_upd AS n_tup_hot_upd,
            Latest.n_live_tup,
            Latest.n_dead_tup,
            Latest.last_vacuum,
            Latest.last_autovacuum,
            Latest.last_analyze,
            Latest.last_autoanalyze
        FROM
            DatabaseTableStats AS Earliest,
            DatabaseTableStats AS Latest
        WHERE
            Earliest.date_created = (
                SELECT min(date_created) FROM DatabaseTableStats
                WHERE date_created >= CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                    - CAST(%s AS interval))
            AND Latest.date_created = (
                SELECT max(date_created) FROM DatabaseTableStats)
            AND Earliest.schemaname = Latest.schemaname
            AND Earliest.relname = Latest.relname
        """ % sqlvalues(options.since_interval)

    cur.execute(tablestats_query)

    # description[0] is the column name, per PEP-0249
    fields = [description[0] for description in cur.description]
    tables = set()
    for row in cur.fetchall():
        table = Table()
        for index in range(len(fields)):
            setattr(table, fields[index], row[index])
        table.total_tup_read = table.seq_tup_read + table.idx_tup_fetch
        table.total_tup_written = (
            table.n_tup_ins + table.n_tup_upd + table.n_tup_del)
        tables.add(table)

    return tables


def get_cpu_stats(cur, options):
    # This query calculates the averate cpu utilization from the
    # samples. It assumes samples are taken at regular intervals over
    # the period.
    query = """
        SELECT (
            CAST(SUM(cpu) AS float) / (
                SELECT COUNT(DISTINCT date_created) FROM DatabaseCpuStats
                WHERE
                    date_created >= (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
                    - CAST (%s AS interval))
            ) AS avg_cpu, username
        FROM DatabaseCpuStats
        WHERE date_created >= (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
            - CAST(%s AS interval))
        GROUP BY username
        """ % sqlvalues(options.since_interval, options.since_interval)

    cur.execute(query)

    return set(cur.fetchall())


def main():
    parser = LPOptionParser()
    db_options(parser)
    parser.add_option(
        "-i", "--interval", dest="since_interval", type=str,
        default="100 years", metavar="INTERVAL",
        help=
            "Use statistics collected over the last INTERVAL period. "
            "INTERVAL is a string parsable by PostgreSQL "
            "such as '5 minutes'.")
    parser.add_option(
        "-n", "--limit", dest="limit", type=int,
        default=15, metavar="NUM",
        help="Display the top NUM items in each category.")
    parser.set_defaults(dbuser="database_stats_report")
    options, args = parser.parse_args()

    con = connect(options.dbuser)
    cur = con.cursor()

    tables = get_table_stats(cur, options)
    arbitrary_table = list(tables)[0]
    interval = arbitrary_table.date_end - arbitrary_table.date_start
    per_second = float(interval.days * 24 * 60 * 60 + interval.seconds)

    print "== Most Read Tables =="
    print
    # These match the pg_user_table_stats view. schemaname is the
    # namespace (normally 'public'), relname is the table (relation)
    # name. total_tup_red is the total number of rows read.
    # idx_tup_fetch is the number of rows looked up using an index.
    tables_sort = ['total_tup_read', 'idx_tup_fetch', 'schemaname', 'relname']
    most_read_tables = sorted(
        tables, key=attrgetter(*tables_sort), reverse=True)
    for table in most_read_tables[:options.limit]:
        print "%40s || %10.2f tuples/sec" % (
            table.relname, table.total_tup_read / per_second)
    print

    print "== Most Written Tables =="
    print
    tables_sort = [
        'total_tup_written', 'n_tup_upd', 'n_tup_ins', 'n_tup_del', 'relname']
    most_written_tables = sorted(
        tables, key=attrgetter(*tables_sort), reverse=True)
    for table in most_written_tables[:options.limit]:
        print "%40s || %10.2f tuples/sec" % (
            table.relname, table.total_tup_written / per_second)
    print

    user_cpu = get_cpu_stats(cur, options)
    print "== Most Active Users =="
    print
    for cpu, username in sorted(user_cpu, reverse=True)[:options.limit]:
        print "%40s || %10.2f%% CPU" % (username, float(cpu) / 10)


if __name__ == '__main__':
    main()

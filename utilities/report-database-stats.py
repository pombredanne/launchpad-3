#!/usr/bin/python -S
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Generate the database statistics report."""

__metaclass__ = type

import _pythonpath

from datetime import datetime
from operator import attrgetter
from textwrap import dedent

from canonical.database.sqlbase import connect, sqlvalues
from canonical.launchpad.scripts import db_options
from lp.scripts.helpers import LPOptionParser


class Table:
    pass


def get_where_clause(options):
    "Generate a WHERE clause referencing the date_created column."
    # We have two of the from timestamp, the until timestamp and an
    # interval. The interval is in a format unsuitable for processing in
    # Python. If the interval is set, it represents the period before
    # the until timestamp or the period after the from timestamp,
    # depending on which of these is set. From this information,
    # generate the SQL representation of the from timestamp and the
    # until timestamp.
    if options.from_ts:
        from_sql = ("CAST(%s AS timestamp without time zone)"
            % sqlvalues(options.from_ts))
    elif options.interval and options.until_ts:
        from_sql = (
            "CAST(%s AS timestamp without time zone) - CAST(%s AS interval)"
            % sqlvalues(options.until_ts, options.interval))
    elif options.interval:
        from_sql = (
            "(CURRENT_TIMESTAMP AT TIME ZONE 'UTC') - CAST(%s AS interval)"
            % sqlvalues(options.interval))
    else:
        from_sql = "CAST('1970-01-01' AS timestamp without time zone)"

    if options.until_ts:
        until_sql = (
            "CAST(%s AS timestamp without time zone)"
            % sqlvalues(options.until_ts))
    elif options.interval and options.from_ts:
        until_sql = (
            "CAST(%s AS timestamp without time zone) + CAST(%s AS interval)"
            % sqlvalues(options.from_ts, options.interval))
    else:
        until_sql = "CURRENT_TIMESTAMP AT TIME ZONE 'UTC'"

    clause = "date_created BETWEEN (%s) AND (%s)" % (from_sql, until_sql)

    return clause


def get_table_stats(cur, options):
    params = {'where': get_where_clause(options)}
    tablestats_query = dedent("""\
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
                WHERE %(where)s)
            AND Latest.date_created = (
                SELECT max(date_created) FROM DatabaseTableStats
                WHERE %(where)s)
            AND Earliest.schemaname = Latest.schemaname
            AND Earliest.relname = Latest.relname
        """ % params)
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
    # Note that we have to use SUM()/COUNT() instead of AVG() as
    # database users not connected when the sample was taken are not
    # recorded - we want the average utilization over the time period,
    # not the subset of the time period the user was actually connected.
    params = {'where': get_where_clause(options)}
    query = dedent("""\
        SELECT (
            CAST(SUM(cpu) AS float) / (
                SELECT COUNT(DISTINCT date_created) FROM DatabaseCpuStats
                WHERE %(where)s
            )) AS avg_cpu, username
        FROM DatabaseCpuStats
        WHERE %(where)s
        GROUP BY username
        """ % params)
    cur.execute(query)
    cpu_stats = set(cur.fetchall())

    # Fold edge into lpnet, as they are now running the same code.
    # This is a temporary hack until we drop edge entirely. See
    # Bug #667883 for details.
    lpnet_avg_cpu = 0.0
    edge_avg_cpu = 0.0
    for stats_tuple in list(cpu_stats):
        avg_cpu, username = stats_tuple
        if username == 'lpnet':
            lpnet_avg_cpu = avg_cpu
            cpu_stats.discard(stats_tuple)
        elif username == 'edge':
            edge_avg_cpu = avg_cpu
            cpu_stats.discard(stats_tuple)
    cpu_stats.add((lpnet_avg_cpu + edge_avg_cpu, 'lpnet'))

    return cpu_stats


def main():
    parser = LPOptionParser()
    db_options(parser)
    parser.add_option(
        "-f", "--from", dest="from_ts", type=datetime,
        default=None, metavar="TIMESTAMP",
        help="Use statistics collected since TIMESTAMP.")
    parser.add_option(
        "-u", "--until", dest="until_ts", type=datetime,
        default=None, metavar="TIMESTAMP",
        help="Use statistics collected up until TIMESTAMP.")
    parser.add_option(
        "-i", "--interval", dest="interval", type=str,
        default=None, metavar="INTERVAL",
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

    if options.from_ts and options.until_ts and options.interval:
        parser.error(
            "Only two of --from, --until and --interval may be specified.")

    con = connect(options.dbuser)
    cur = con.cursor()

    tables = list(get_table_stats(cur, options))
    if len(tables) == 0:
        parser.error("No statistics available in that time range.")
    arbitrary_table = tables[0]
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

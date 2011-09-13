#!/usr/bin/python2.6 -S
# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Confirm the database systems are ready to be patched as best we can."""

import _pythonpath

__all__ = [
    'DatabasePreflight',
    'KillConnectionsPreflight',
    'NoConnectionCheckPreflight',
    ]


from datetime import timedelta
from optparse import OptionParser
import time

import psycopg2

from canonical.database.sqlbase import (
    connect,
    ISOLATION_LEVEL_AUTOCOMMIT,
    sqlvalues,
    )
from canonical.launchpad.scripts import (
    db_options,
    logger,
    logger_options,
    )
import replication.helpers


# Ignore connections by these users.
SYSTEM_USERS = frozenset(['postgres', 'slony', 'nagios', 'lagmon'])

# Fail checks if these users are connected. If a process should not be
# interrupted by a rollout, the database user it connects as should be
# added here. The preflight check will fail if any of these users are
# connected, so these systems will need to be shut down manually before
# a database update.
FRAGILE_USERS = frozenset(['archivepublisher', 'fiera'])

# How lagged the cluster can be before failing the preflight check.
MAX_LAG = timedelta(seconds=60)


class DatabasePreflight:
    def __init__(self, log):
        master_con = connect(isolation=ISOLATION_LEVEL_AUTOCOMMIT)

        self.log = log
        self.is_replicated = replication.helpers.slony_installed(master_con)
        if self.is_replicated:
            self.nodes = set(
                replication.helpers.get_all_cluster_nodes(master_con))
            for node in self.nodes:
                node.con = psycopg2.connect(node.connection_string)
                node.con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

            # Create a list of nodes subscribed to the replicated sets we
            # are modifying.
            cur = master_con.cursor()
            cur.execute("""
                WITH subscriptions AS (
                    SELECT *
                    FROM _sl.sl_subscribe
                    WHERE sub_set = 1 AND sub_active IS TRUE)
                SELECT sub_provider FROM subscriptions
                UNION
                SELECT sub_receiver FROM subscriptions
                """)
            lpmain_node_ids = set(row[0] for row in cur.fetchall())
            self.lpmain_nodes = set(
                node for node in self.nodes
                if node.node_id in lpmain_node_ids)
        else:
            node = replication.helpers.Node(None, None, None, True)
            node.con = master_con
            self.nodes = set([node])
            self.lpmain_nodes = self.nodes

    def check_is_superuser(self):
        """Return True if all the node connections are as superusers."""
        success = True
        for node in self.nodes:
            cur = node.con.cursor()
            cur.execute("""
                SELECT current_database(), pg_user.usesuper
                FROM pg_user
                WHERE usename = current_user
                """)
            dbname, is_super = cur.fetchone()
            if is_super:
                self.log.debug("Connected to %s as a superuser.", dbname)
            else:
                self.log.fatal("Not connected to %s as a superuser.", dbname)
                success = False
        return success

    def check_open_connections(self):
        """False if any lpmain nodes have connections from non-system users.

        We only check on subscribed nodes, as there will be active systems
        connected to other nodes in the replication cluster (such as the
        SSO servers).

        System users are defined by SYSTEM_USERS.
        """
        success = True
        for node in self.lpmain_nodes:
            cur = node.con.cursor()
            cur.execute("""
                SELECT datname, usename, COUNT(*) AS num_connections
                FROM pg_stat_activity
                WHERE
                    datname=current_database()
                    AND procpid <> pg_backend_pid()
                GROUP BY datname, usename
                """)
            for datname, usename, num_connections in cur.fetchall():
                if usename in SYSTEM_USERS:
                    self.log.debug(
                        "%s has %d connections by %s",
                        datname, num_connections, usename)
                else:
                    self.log.fatal(
                        "%s has %d connections by %s",
                        datname, num_connections, usename)
                    success = False
        if success:
            self.log.info("Only system users connected to the cluster")
        return success

    def check_fragile_connections(self):
        """Fail if any FRAGILE_USERS are connected to the cluster.

        If we interrupt these processes, we may have a mess to clean
        up. If they are connected, the preflight check should fail.
        """
        success = True
        for node in self.lpmain_nodes:
            cur = node.con.cursor()
            cur.execute("""
                SELECT datname, usename, COUNT(*) AS num_connections
                FROM pg_stat_activity
                WHERE
                    datname=current_database()
                    AND procpid <> pg_backend_pid()
                    AND usename IN %s
                GROUP BY datname, usename
                """ % sqlvalues(FRAGILE_USERS))
            for datname, usename, num_connections in cur.fetchall():
                self.log.fatal(
                    "Fragile system %s running. %s has %d connections.",
                    usename, datname, num_connections)
                success = False
        if success:
            self.log.info(
                "No fragile systems connected to the cluster (%s)"
                % ', '.join(FRAGILE_USERS))
        return success

    def check_long_running_transactions(self, max_secs=60):
        """Return False if any nodes have long running transactions open.

        max_secs defines what is long running. For database rollouts,
        this will be short. Even if the transaction is benign like a
        autovacuum task, we should wait until things have settled down.
        """
        success = True
        for node in self.nodes:
            cur = node.con.cursor()
            cur.execute("""
                SELECT
                    datname, usename,
                    age(current_timestamp, xact_start) AS age, current_query
                FROM pg_stat_activity
                WHERE
                    age(current_timestamp, xact_start) > interval '%d secs'
                    AND datname=current_database()
                """ % max_secs)
            for datname, usename, age, current_query in cur.fetchall():
                self.log.fatal(
                    "%s has transaction by %s open %s",
                    datname, usename, age)
                success = False
        if success:
            self.log.info("No long running transactions detected.")
        return success

    def check_replication_lag(self):
        """Return False if the replication cluster is badly lagged."""
        if not self.is_replicated:
            self.log.debug("Not replicated - no replication lag.")
            return True

        # Check replication lag on every node just in case there are
        # disagreements.
        max_lag = timedelta(seconds=-1)
        for node in self.nodes:
            cur = node.con.cursor()
            cur.execute("""
                SELECT current_database(),
                max(st_lag_time) AS lag FROM _sl.sl_status
            """)
            dbname, lag = cur.fetchone()
            if lag > max_lag:
                max_lag = lag
            self.log.debug(
                "%s reports database lag of %s.", dbname, lag)
        if max_lag <= MAX_LAG:
            self.log.info("Database cluster lag is ok (%s)", max_lag)
            return True
        else:
            self.log.fatal("Database cluster lag is high (%s)", max_lag)
            return False

    def check_can_sync(self):
        """Return True if a sync event is acknowledged by all nodes.

        We only wait 30 seconds for the sync, because we require the
        cluster to be quiescent.
        """
        if self.is_replicated:
            success = replication.helpers.sync(30, exit_on_fail=False)
            if success:
                self.log.info(
                    "Replication events are being propagated.")
            else:
                self.log.fatal(
                    "Replication events are not being propagated.")
                self.log.fatal(
                    "One or more replication daemons may be down.")
                self.log.fatal(
                    "Bounce the replication daemons and check the logs.")
            return success
        else:
            return True

    def check_all(self):
        """Run all checks.

        If any failed, return False. Otherwise return True.
        """
        if not self.check_is_superuser():
            # No point continuing - results will be bogus without access
            # to pg_stat_activity
            return False

        success = True
        if not self.check_replication_lag():
            success = False
        if not self.check_can_sync():
            success = False
        # Do checks on open transactions last to minimize race
        # conditions.
        if not self.check_open_connections():
            success = False
        if not self.check_long_running_transactions():
            success = False
        if not self.check_fragile_connections():
            success = False
        return success


class NoConnectionCheckPreflight(DatabasePreflight):
    def check_open_connections(self):
        return True


class KillConnectionsPreflight(DatabasePreflight):
    def check_open_connections(self):
        """Kill all non-system connections to Launchpad databases.

        We only check on subscribed nodes, as there will be active systems
        connected to other nodes in the replication cluster (such as the
        SSO servers).

        System users are defined by SYSTEM_USERS.
        """
        # We keep trying to terminate connections every 0.5 seconds for
        # up to 10 seconds.
        num_tries = 20
        seconds_to_pause = 0.5
        for loop_count in range(num_tries):
            all_clear = True
            for node in self.lpmain_nodes:
                cur = node.con.cursor()
                cur.execute("""
                    SELECT
                        procpid, datname, usename,
                        pg_terminate_backend(procpid)
                    FROM pg_stat_activity
                    WHERE
                        datname=current_database()
                        AND procpid <> pg_backend_pid()
                        AND usename NOT IN %s
                    """ % sqlvalues(SYSTEM_USERS))
                for procpid, datname, usename, ignored in cur.fetchall():
                    all_clear = False
                    if loop_count == num_tries - 1:
                        self.log.fatal(
                            "Unable to kill %s [%s] on %s",
                            usename, procpid, datname)
                    else:
                        self.log.warning(
                            "Killed %s [%s] on %s", usename, procpid, datname)
            if all_clear:
                break

            # Wait a little for any terminated connections to actually
            # terminate.
            time.sleep(seconds_to_pause)
        return all_clear


def main():
    parser = OptionParser()
    db_options(parser)
    logger_options(parser)
    parser.add_option(
        "--skip-connection-check", dest='skip_connection_check',
        default=False, action="store_true",
        help="Don't check open connections.")
    parser.add_option(
        "--kill-connections", dest='kill_connections',
        default=False, action="store_true",
        help="Kill non-system connections instead of reporting an error.")
    (options, args) = parser.parse_args()
    if args:
        parser.error("Too many arguments")

    if options.kill_connections and options.skip_connection_check:
        parser.error(
            "--skip-connection-check conflicts with --kill-connections")

    log = logger(options)

    if options.kill_connections:
        preflight_check = KillConnectionsPreflight(log)
    elif options.skip_connection_check:
        preflight_check = NoConnectionCheckPreflight(log)
    else:
        preflight_check = DatabasePreflight(log)

    if preflight_check.check_all():
        log.info('Preflight check succeeded. Good to go.')
        return 0
    else:
        log.error('Preflight check failed.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

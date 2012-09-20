#!/usr/bin/python -S
# Copyright 2011-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Full update process."""

import _pythonpath

from datetime import datetime
from optparse import OptionParser
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import NamedTupleConnection
import sys

from lp.services.database.postgresql import ConnectionString
from lp.services.scripts import (
    logger,
    logger_options,
    )
from preflight import (
    KillConnectionsPreflight,
    NoConnectionCheckPreflight,
    streaming_sync,
    SYSTEM_USERS
    )
import security  # security.py script
import upgrade  # upgrade.py script


# Increase this timeout once we are confident in the
# implementation. We don't want to block rollouts
# unnecessarily with slow timeouts and a flaky sync
# detection implementation.
STREAMING_SYNC_TIMEOUT = 60


def run_upgrade(options, log, master_con):
    """Invoke upgrade.py in-process.

    It would be easier to just invoke the script, but this way we save
    several seconds of overhead as the component architecture loads up.
    """
    # Fake expected command line arguments and global log
    upgrade.options = options
    upgrade.log = log
    # upgrade.py doesn't commit, because we are sharing the transaction
    # with security.py. We want schema updates and security changes
    # applied in the same transaction.
    options.commit = False
    options.partial = False
    # Invoke the database schema upgrade process.
    try:
        return upgrade.main(master_con)
    except Exception:
        log.exception('Unhandled exception')
        return 1
    except SystemExit as x:
        log.fatal("upgrade.py failed [%s]", x)


def run_security(options, log, master_con):
    """Invoke security.py in-process.

    It would be easier to just invoke the script, but this way we save
    several seconds of overhead as the component architecture loads up.
    """
    # Fake expected command line arguments and global log
    options.dryrun = False
    options.revoke = True
    options.owner = 'postgres'
    security.options = options
    security.log = log
    # Invoke the database security reset process.
    try:
        return security.main(options, master_con)
    except Exception:
        log.exception('Unhandled exception')
        return 1
    except SystemExit as x:
        log.fatal("security.py failed [%s]", x)


def pg_connect(conn_str):
    con = psycopg2.connect(
        str(conn_str), connection_factory=NamedTupleConnection)
    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return con


class DBController:
    def __init__(self, log, pgbouncer_conn_str, dbname, dbuser):
        self.log = log
        self.pgbouncer_con = pg_connect(pgbouncer_conn_str)

        self.master_name = None
        self.master = None
        self.slaves = {}

        for db in self.pgbouncer_cmd('show databases', results=True):
            if db.database != dbname:
                continue

            conn_str = 'dbname=%s port=%s user=%s' % (dbname, db.port, dbuser)
            if db.host:
                conn_str += ' host=%s' % db.host
            con = pg_connect(conn_str)
            cur = con.cursor()
            cur.execute('select pg_is_in_recovery()')
            if cur.fetchone()[0] is True:
                self.slaves[db.name] = conn_str
            else:
                self.master_name = db.name
                self.master = conn_str

        if self.master_name is None:
            log.fatal('No master detected.')
            raise SystemExit(98)

    def pgbouncer_cmd(self, cmd, results):
        cur = self.pgbouncer_con.cursor()
        cur.execute(cmd)
        if results:
            return cur.fetchall()

    def pause_replication(self):
        names = self.slaves.keys()
        self.log.info("Pausing replication to %s.", ', '.join(names))
        for name, conn_str in self.slaves.items():
            try:
                con = pg_connect(conn_str)
                cur = con.cursor()
                cur.execute('select pg_xlog_replay_pause()')
            except psycopg2.Error, x:
                self.log.error(
                    'Unable to pause replication to %s (%s).'
                    % (name, str(x)))
                return False
        return True

    def resume_replication(self):
        names = self.slaves.keys()
        self.log.info("Resuming replication to %s.", ', '.join(names))
        success = True
        for name, conn_str in self.slaves.items():
            try:
                con = pg_connect(conn_str)
                cur = con.cursor()
                cur.execute('select pg_xlog_replay_resume()')
            except psycopg2.Error, x:
                success = False
                self.log.error(
                    'Failed to resume replication to %s (%s).'
                    % (name, str(x)))
        return success

    def ensure_replication_enabled(self):
        """Force replication back on.

        It may have been disabled if a previous run failed horribly,
        or just admin error. Either way, we are trying to make the
        scheduled downtime window so automate this.
        """
        success = True
        wait_for_sync = False
        for name, conn_str in self.slaves.items():
            try:
                con = pg_connect(conn_str)
                cur = con.cursor()
                cur.execute("SELECT pg_is_xlog_replay_paused()")
                replication_paused = cur.fetchone()[0]
                if replication_paused:
                    self.log.warn("Replication paused on %s. Resuming.", name)
                    cur.execute("SELECT pg_xlog_replay_resume()")
                    wait_for_sync = True
            except psycopg2.Error, x:
                success = False
                self.log.error(
                    "Failed to resume replication on %s (%s)", name, str(x))
        if success and wait_for_sync:
            self.sync()
        return success

    def disable(self, name):
        try:
            self.pgbouncer_cmd("DISABLE %s" % name, results=False)
            self.pgbouncer_cmd("KILL %s" % name, results=False)
            return True
        except psycopg2.Error, x:
            self.log.error("Unable to disable %s (%s)", name, str(x))
            return False

    def enable(self, name):
        try:
            self.pgbouncer_cmd("RESUME %s" % name, results=False)
            self.pgbouncer_cmd("ENABLE %s" % name, results=False)
            return True
        except psycopg2.Error, x:
            self.log.error("Unable to enable %s (%s)", name, str(x))
            return False

    def disable_master(self):
        self.log.info("Disabling access to %s.", self.master_name)
        return self.disable(self.master_name)

    def enable_master(self):
        self.log.info("Reenabling access to %s.", self.master_name)
        return self.enable(self.master_name)

    def disable_slaves(self):
        names = self.slaves.keys()
        self.log.info(
            "Disabling access to %s.", ', '.join(names))
        for name in self.slaves.keys():
            if not self.disable(name):
                return False  # Don't do further damage if we failed.
        return True

    def enable_slaves(self):
        names = self.slaves.keys()
        self.log.info(
            "Reenabling access to %s.", ', '.join(names))
        success = True
        for name in self.slaves.keys():
            if not self.enable(name):
                success = False
        return success

    def sync(self):
        sync = streaming_sync(pg_connect(self.master), STREAMING_SYNC_TIMEOUT)
        if sync:
            self.log.debug('Slaves in sync.')
        else:
            self.log.error(
                'Slaves failed to sync after %d seconds.',
                STREAMING_SYNC_TIMEOUT)
        return sync


def main():
    parser = OptionParser()

    parser.add_option(
        '--pgbouncer', dest='pgbouncer',
        default='host=localhost port=6432 user=pgbouncer',
        metavar='CONN_STR',
        help="libpq connection string to administer pgbouncer")

    parser.add_option(
        '--dbname', dest='dbname', default='launchpad_prod', metavar='DBNAME',
        help='Database name we are updating.')

    parser.add_option(
        '--dbuser', dest='dbuser', default='postgres', metavar='USERNAME',
        help='Connect as USERNAME to databases')

    logger_options(parser)
    (options, args) = parser.parse_args()
    if args:
        parser.error("Too many arguments")

    # In case we are connected as a non-standard superuser, ensure we
    # don't kill our own connections.
    SYSTEM_USERS.add(options.dbuser)

    log = logger(options)

    # Connection string to administrate pgbouncer, required.
    pgbouncer_conn_str = ConnectionString(options.pgbouncer)
    if not pgbouncer_conn_str.dbname:
        pgbouncer_conn_str.dbname = 'pgbouncer'
    if pgbouncer_conn_str.dbname != 'pgbouncer':
        log.warn("pgbouncer administrative database not named 'pgbouncer'")

    controller = DBController(
        log, pgbouncer_conn_str, options.dbname, options.dbuser)
    slaves = controller.slaves.values()

    try:
        # Master connection, not running in autocommit to allow us to
        # rollback changes on failure.
        master_con = psycopg2.connect(controller.master)
    except Exception, x:
        log.fatal("Unable to open connection to master db (%s)", str(x))
        return 94

    # Preflight checks. Confirm as best we can that the upgrade will
    # work unattended. Here we ignore open connections, as they
    # will shortly be killed.
    controller.ensure_replication_enabled()
    if not NoConnectionCheckPreflight(log, slaves).check_all():
        return 99

    #
    # Start the actual upgrade. Failures beyond this point need to
    # generate informative messages to help with recovery.
    #

    # status flags
    upgrade_run = False
    security_run = False
    replication_paused = False
    master_disabled = False
    slaves_disabled = False
    outage_start = None

    try:
        # Pause replication.
        replication_paused = controller.pause_replication()
        if not replication_paused:
            return 93

        # Start the outage clock.
        log.info("Outage starts.")
        outage_start = datetime.now()

        # Disable access and kill connections to the master database.
        master_disabled = controller.disable_master()
        if not master_disabled:
            return 95

        if not KillConnectionsPreflight(
            log, slaves, replication_paused=replication_paused).check_all():
            return 100

        log.info("Preflight check succeeded. Starting upgrade.")
        # Does not commit master_con, even on success.
        upgrade_rc = run_upgrade(options, log, master_con)
        upgrade_run = (upgrade_rc == 0)
        if not upgrade_run:
            return upgrade_rc
        log.info("Database patches applied. Stored procedures updated.")

        # Commits master_con on success.
        security_rc = run_security(options, log, master_con)
        security_run = (security_rc == 0)
        if not security_run:
            return security_rc

        log.info("Master database updated. Reenabling.")
        master_disabled = not controller.enable_master()
        if master_disabled:
            log.warn("Outage ongoing until pgbouncer bounced.")
            return 96
        else:
            log.info("Outage complete. %s", datetime.now() - outage_start)

        slaves_disabled = controller.disable_slaves()

        # Resume replication.
        log.info("Resuming replication.")
        replication_paused = not controller.resume_replication()
        if replication_paused:
            log.error(
                "Failed to resume replication. Run pg_xlog_replay_pause() "
                "on all slaves to manually resume.")
        else:
            controller.sync()

        if slaves_disabled:
            log.info("Enabling slave database connections.")
            slaves_disabled = not controller.enable_slaves()
            if slaves_disabled:
                log.warn(
                    "Failed to enable slave databases in pgbouncer. "
                    "Now running in master-only mode.")

        # We will start seeing connections as soon as pgbouncer is
        # reenabled, so ignore them here.
        if not NoConnectionCheckPreflight(log, slaves).check_all():
            return 101

        log.info("All good. All done.")
        return 0

    finally:
        if not security_run:
            log.warning("Rolling back all schema and security changes.")
            master_con.rollback()

        # Recovery if necessary.
        if master_disabled:
            if controller.enable_master():
                log.warning(
                    "Master reenabled despite earlier failures. "
                    "Outage over %s, but we have problems"
                    % str(datetime.now() - outage_start))
            else:
                log.warning(
                    "Master is still disabled in pgbouncer. Outage ongoing.")

        if replication_paused:
            if controller.resume_replication():
                log.info("Replication resumed despite earlier failures")

        if slaves_disabled:
            if controller.enable_slaves():
                log.info("Slave database connections reenabled.")


if __name__ == '__main__':
    sys.exit(main())

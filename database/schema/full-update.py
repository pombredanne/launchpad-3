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
    streaming_sync
    )
import security  # security.py script
import upgrade  # upgrade.py script


def run_upgrade(options, log):
    """Invoke upgrade.py in-process.

    It would be easier to just invoke the script, but this way we save
    several seconds of overhead as the component architecture loads up.
    """
    # Fake expected command line arguments and global log
    options.commit = True
    options.partial = False
    upgrade.options = options
    upgrade.log = log
    # Invoke the database schema upgrade process.
    try:
        return upgrade.main()
    except Exception:
        log.exception('Unhandled exception')
        return 1
    except SystemExit as x:
        log.fatal("upgrade.py failed [%s]", x)


def run_security(options, log):
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
        return security.main(options)
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
    def __init__(self, log, pgbouncer_conn_str, dbname):
        self.log = log
        self.pgbouncer_con = pg_connect(pgbouncer_conn_str)

        self.master_name = None
        self.master = None
        self.slaves = {}

        for db in self.pgbouncer_cmd('show databases'):
            if db.database != dbname:
                continue

            conn_str = 'dbname=%s port=%s' % (dbname, db.port)
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
            log.fatal('No master detected')
            raise SystemExit(98)

    def pgbouncer_cmd(self, cmd):
        cur = self.pgbouncer_con.cursor()
        cur.execute(cmd)
        return cur.fetchall()

    def pause_replication(self):
        self.log.info('Pausing replication')
        for name, conn_str in self.slaves.items():
            try:
                con = pg_connect(conn_str)
                cur = con.cursor()
                cur.execute('select pg_xlog_replay_pause()')
            except psycopg2.Error, x:
                self.log.error(
                    'Unable to pause replication of %s (%s)'
                    % (name, str(x)))
                return False
        return True

    def resume_replication(self):
        self.log.info('Resuming replication')
        success = True
        for name, conn_str in self.slaves.items():
            try:
                con = pg_connect(conn_str)
                cur = con.cursor()
                cur.execute('select pg_xlog_replay_pause()')
            except psycopg2.Error, x:
                success = False
                self.log.error(
                    'Failed to resume replication on %s (%s)'
                    % (name, str(x)))
        return success

    def disable(self, name):
        try:
            self.pgbouncer_cmd("DISABLE %s" % name)
            self.pgbouncer_cmd("KILL %s" % name)
            return True
        except psycopg2.Error, x:
            self.log.error("Unable to disable %s (%s)", name, str(x))

    def enable(self, name):
        try:
            self.pgbouncer_cmd("RESUME %s" % name)
            self.pgbouncer_cmd("ENABLE %s" % name)
            return True
        except psycopg2.Error, x:
            self.log.error("Unable to enable %s (%s)", name, str(x))

    def disable_master(self):
        return self.disable(self.master_name)

    def enable_master(self):
        return self.enable(self.master_name)

    def disable_slaves(self):
        for name in self.slaves.keys():
            if not self.disable(name):
                return False  # Don't do further damage if we failed.
        return True

    def enable_slaves(self):
        success = True
        for name in self.slaves.keys():
            if not self.enable(name):
                success = False
        return success

    def sync(self, timeout):
        return streaming_sync(pg_connect(self.master), timeout)


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

    logger_options(parser)
    (options, args) = parser.parse_args()
    if args:
        parser.error("Too many arguments")

    log = logger(options)

    # Connection string to administrate pgbouncer, required.
    pgbouncer_conn_str = ConnectionString(options.pgbouncer)
    if not pgbouncer_conn_str.dbname:
        pgbouncer_conn_str.dbname = 'pgbouncer'
    if pgbouncer_conn_str.dbname != 'pgbouncer':
        log.warn("pgbouncer administrative database not named 'pgbouncer'")

    controller = DBController(log, pgbouncer_conn_str, options.dbname)
    slaves = controller.slaves.values()
    #
    # Preflight checks. Confirm as best we can that the upgrade will
    # work unattended.
    #

    # We initially ignore open connections, as they will shortly be
    # killed.
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

    try:
        # Stop replication on slaves
        replication_paused = controller.pause_replication()
        if not replication_paused:
            return 94

        # Disable access and kill connections to the master database.
        log.info("Outage starts. Disabling access to master db.")
        outage_start = datetime.now()
        master_disabled = controller.disable_master()
        if not master_disabled:
            return 95

        if not KillConnectionsPreflight(log, slaves).check_all():
            return 100

        log.info("Preflight check succeeded. Starting upgrade.")
        upgrade_rc = run_upgrade(options, log)
        if upgrade_rc != 0:
            return upgrade_rc
        upgrade_run = True
        log.info("Database patches applied. Stored procedures updated.")

        security_rc = run_security(options, log)
        if security_rc != 0:
            return security_rc
        security_run = True

        log.info("Master database updated. Reenabling.")
        master_disabled = not controller.enable_master()
        if master_disabled:
            log.warn("Outage ongoing until pgbouncer bounced!")
            return 96
        else:
            log.info("Outage complete. %s", datetime.now() - outage_start)

        log.info("Disabling slaves")
        slaves_disabled = controller.disable_slaves()
        if not slaves_disabled:
            return 97

        log.info("Resuming replication")
        replication_paused = not controller.resume_replication()
        if replication_paused:
            return 98

        # Increase this timeout once we are confident in the implementation.
        # We don't want to block rollouts unnecessarily with slow
        # timeouts and a flaky sync detection implementation.
        streaming_sync_timeout = 120

        sync = controller.wait_for_sync(streaming_sync_timeout)

        if sync:
            log.debug('Streaming replicas in sync.')
        else:
            log.error(
                'Streaming replicas failed to sync after %d seconds.',
                streaming_sync_timeout)

        log.info("Enabling slaves")
        slaves_disabled = not controller.enable_slaves()

        # We will start seeing connections as soon as pgbouncer is
        # reenabled, so ignore them here.
        if not NoConnectionCheckPreflight(log, slaves).check_all():
            return 101

        log.info("All good. All done.")
        return 0

    finally:
        # Recovery if necessary.
        if replication_paused:
            if controller.resume_replication():
                log.info("Replication resumed despite earlier failures")
            else:
                log.warning(
                    "Replication disabled. Run pg_xlog_replay_resume() "
                    "on slaves")

        if master_disabled:
            if controller.enable_master():
                log.info("Master reenabled despite earlier failures")
            else:
                log.warning("Master is still disabled in pgbouncer")

        if slaves_disabled:
            if controller.enable_slaves():
                log.info("Slaves reenabled despite earlier failures")
            else:
                log.warning("Slaves are still disabled in pgbouncer")

        if not upgrade_run:
            log.warning("upgrade.py still needs to be run")

        if not security_run:
            log.warning("security.py still needs to be run")


if __name__ == '__main__':
    sys.exit(main())

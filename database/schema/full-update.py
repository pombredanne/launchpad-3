#!/usr/bin/python2.6 -S
# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Full update process."""

import _pythonpath

from datetime import datetime
from optparse import OptionParser
import subprocess
import sys

from canonical.launchpad.scripts import (
    db_options,
    logger,
    logger_options,
    )

from preflight import (
    KillConnectionsPreflight,
    NoConnectionCheckPreflight,
    )
import security  # security.py script
import upgrade  # upgrade.py script


PGBOUNCER_INITD = ['sudo', '/etc/init.d/pgbouncer']


def run_pgbouncer(log, cmd):
    """Invoke the pgbouncer initscript.

    :param cmd: One of 'start', 'stop' or 'status'.
    """
    assert cmd in ('start', 'stop', 'status'), '''
        Unrecognized command; remember any new commands need to be
        granted sudo on staging and prod.
        '''
    pgbouncer_rc = subprocess.call(PGBOUNCER_INITD + [cmd])
    sys.stdout.flush()
    if pgbouncer_rc != 0:
        log.error("pgbouncer '%s' failed [%s]", cmd, pgbouncer_rc)
    return pgbouncer_rc


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
    except SystemExit, x:
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
    options.cluster = True
    security.options = options
    security.log = log
    # Invoke the database security reset process.
    try:
        return security.main(options)
    except Exception:
        log.exception('Unhandled exception')
        return 1
    except SystemExit, x:
        log.fatal("security.py failed [%s]", x)


def main():
    parser = OptionParser()

    # Add all the command command line arguments.
    db_options(parser)
    logger_options(parser)
    (options, args) = parser.parse_args()
    if args:
        parser.error("Too many arguments")

    log = logger(options)

    #
    # Preflight checks. Confirm as best we can that the upgrade will
    # work unattended.
    #

    # Confirm we can invoke PGBOUNCER_INITD
    log.debug("Confirming sudo access to pgbouncer startup script")
    pgbouncer_rc = run_pgbouncer(log, 'status')
    if pgbouncer_rc != 0:
        return pgbouncer_rc

    # We initially ignore open connections, as they will shortly be
    # killed.
    if not NoConnectionCheckPreflight(log).check_all():
        return 99

    #
    # Start the actual upgrade. Failures beyond this point need to
    # generate informative messages to help with recovery.
    #

    # status flags
    pgbouncer_down = False
    upgrade_run = False
    security_run = False

    outage_start = datetime.now()

    try:
        # Shutdown pgbouncer
        log.info("Outage starts. Shutting down pgbouncer.")
        pgbouncer_rc = run_pgbouncer(log, 'stop')
        if pgbouncer_rc != 0:
            log.fatal("pgbouncer not shut down [%s]", pgbouncer_rc)
            return pgbouncer_rc
        pgbouncer_down = True

        if not KillConnectionsPreflight(log).check_all():
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

        log.info("All database upgrade steps completed")

        log.info("Restarting pgbouncer")
        pgbouncer_rc = run_pgbouncer(log, 'start')
        if pgbouncer_rc != 0:
            log.fatal("pgbouncer not restarted [%s]", pgbouncer_rc)
            return pgbouncer_rc
        pgbouncer_down = False
        log.info("Outage complete. %s", datetime.now() - outage_start)

        # We will start seeing connections as soon as pgbouncer is
        # reenabled, so ignore them here.
        if not NoConnectionCheckPreflight(log).check_all():
            return 101

        log.info("All good. All done.")
        return 0

    finally:
        if pgbouncer_down:
            # Even if upgrade.py or security.py failed, we should be in
            # a good enough state to continue operation so restart
            # pgbouncer and allow connections.
            #  - upgrade.py may have failed to update the master, and
            #    changes should have rolled back.
            #  - upgrade.py may have failed to update a slave, breaking
            #    replication. The master is still operational, but
            #    slaves may be lagging and have the old schema.
            #  - security.py may have died, rolling back its changes on
            #    one or more nodes.
            # In all cases except the first, we have recovery to do but
            # systems are probably ok, or at least providing some
            # services.
            pgbouncer_rc = run_pgbouncer(log, 'start')
            if pgbouncer_rc == 0:
                log.info("Despite failures, pgbouncer restarted.")
                log.info("Outage complete. %s", datetime.now() - outage_start)
            else:
                log.fatal("pgbouncer is down and refuses to restart")
        if not upgrade_run:
            log.warning("upgrade.py still needs to be run")
        if not security_run:
            log.warning("security.py still needs to be run")


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/python2.6 -S
# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Full update process."""

import _pythonpath

import os.path
from optparse import OptionParser
import subprocess
import sys

from canonical.launchpad.scripts import (
    db_options,
    logger,
    logger_options,
    )

from preflight import (
    DatabasePreflight,
    KillConnectionsPreflight,
    NoConnectionCheckPreflight,
    )


PGBOUNCER_INITD = ['sudo', '/etc/init.d/pgbouncer']


def run_script(script, *extra_args):
    script_path = os.path.join(os.path.dirname(__file__), script)
    return subprocess.call([script_path] + sys.argv[1:] + list(extra_args))


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

    # We initially ignore open connections, as they will shortly be
    # killed.
    if not NoConnectionCheckPreflight(log).check_all():
        return 99

    # Confirm we can invoke PGBOUNCER_INITD
    pgbouncer_status_cmd = PGBOUNCER_INITD + ['status']
    pgbouncer_rc = subprocess.call(pgbouncer_status_cmd)
    sys.stdout.flush()
    if pgbouncer_rc != 0:
        log.fatal("Unable to invoke %s", ' '.join(pgbouncer_status_cmd))
        return pgbouncer_rc

    #
    # Start the actual upgrade. Failures beyond this point need to
    # generate informative messages to help with recovery.
    #

    # status flags
    pgbouncer_down = False
    upgrade_run = False
    # Bug #815717
    # fti_run = False
    security_run = False

    try:
        # Shutdown pgbouncer
        pgbouncer_rc = subprocess.call(PGBOUNCER_INITD + ['stop'])
        sys.stdout.flush()
        if pgbouncer_rc != 0:
            log.fatal("pgbouncer not shut down [%s]", pgbouncer_rc)
            return pgbouncer_rc
        pgbouncer_down = True

        if not KillConnectionsPreflight(log).check_all():
            return 100

        # upgrade.py needs to be refactored before including inline,
        # as it invokes sys.exit() on various failures. Running it
        # in process would be nice as it will save a few seconds of
        # runtime.
        upgrade_rc = run_script('upgrade.py')
        if upgrade_rc != 0:
            log.warning("upgrade.py run may have been partial")
            return upgrade_rc
        upgrade_run = True

        # fti.py is no longer being run on production. Updates
        # to full text indexes need to be handled manually in db
        # patches. Bug #815717.
        # fti_rc = run_script('fti.py')
        # if fti_rc != 0:
        #     return fti_rc
        # fti_run = True

        security_rc = run_script('security.py', '--cluster')
        if security_rc != 0:
            return security_rc
        security_run = True

        log.info("All database upgrade steps completed")

        pgbouncer_rc = subprocess.call(PGBOUNCER_INITD + ['start'])
        sys.stdout.flush()
        if pgbouncer_rc != 0:
            log.fatal("pgbouncer not restarted [%s]", pgbouncer_rc)
            return pgbouncer_rc
        pgbouncer_down = False

        # We will start seeing connections as soon as pgbouncer is
        # reenabled, so ignore them here.
        if not NoConnectionCheckPreflight(log).check_all():
            return 101

        log.info("All good. All done.")
        return 0

    finally:
        if pgbouncer_down:
            log.warning("pgbouncer is down and will need to be restarted")
        if not upgrade_run:
            log.warning("upgrade.py still needs to be run")
        # Bug #815717
        # if not fti_run:
        #     log.warning("fti.py still needs to be run")
        if not security_run:
            log.warning("security.py still needs to be run")


if __name__ == '__main__':
    sys.exit(main())

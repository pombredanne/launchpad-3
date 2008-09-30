#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Startup and shutdown slon processes.

On production and staging we probably want to use the standard
/etc/init.d/slony1 script instead of this tool.
"""

import _pythonpath

import os.path
import subprocess
import sys
from optparse import OptionParser

from canonical.config import config
from canonical.database.postgresql import ConnectionString
from canonical.launchpad.scripts import logger, logger_options
import replication.helpers

__metaclass__ = type
__all__ = []


def main():
    parser = OptionParser("Usage: %prog [options] [start|stop]")
    logger_options(parser)
    options, args = parser.parse_args()

    if len(args) == 0:
        parser.error("No command given.")

    if len(args) != 1:
        parser.error("Only one command allowed.")

    command = args[0]
    if command not in ['start', 'stop']:
        parser.error("Unknown command %s." % command)

    log = logger()

    assert config.database.main_master != config.database.main_slave, (
        "Master and slave identical - LPCONFIG not a replicated setup.")

    for instance in ['main_master', 'main_slave']:
        pidfile = os.path.join(
            config.canonical.pid_dir, 'lpslon_%s.pid' % instance)
        logfile = os.path.join(
            config.root, 'database', 'replication',
            'lpslon_%s.log' % instance)
        connection_string = ConnectionString(
            getattr(config.database, instance))
        connection_string.user = 'slony'
        if command == 'start':
            log.info("Starting %s slon daemon." % instance)
            log.debug("Logging to %s" % logfile)
            log.debug("PID file %s" % pidfile)
            cmd = [
                "start-stop-daemon",
                "--start",
                "--background",
                "--pidfile", pidfile,
                "--exec", "/usr/bin/slon",
                "--startas", "/bin/sh",
                "--", "-c",
                "slon -d 2 -p %s %s '%s' > %s" % (
                    pidfile, replication.helpers.CLUSTERNAME,
                    connection_string, logfile)]
        else:
            if not os.path.exists(pidfile):
                log.info(
                    "%s slon daemon not running. Doing nothing." % instance)
                continue
            log.info("Stopping %s slon daemon." % instance)
            log.debug("PID file %s" % pidfile)
            cmd = [
                "start-stop-daemon",
                "--stop",
                "--pidfile", pidfile]
        log.debug("Running %s" % repr(cmd))
        return_code = subprocess.call(cmd)
        if return_code != 0:
            log.fatal("Failed. Return code %s" % return_code)
            return return_code


if __name__ == '__main__':
    sys.exit(main())

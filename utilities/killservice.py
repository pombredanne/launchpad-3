#!/usr/bin/python2.4

# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import _pythonpath

import os, sys, logging
from signal import SIGTERM
from optparse import OptionParser
from canonical.pidfile import pidfile_path
from canonical.launchpad.scripts import logger_options, logger


if __name__ == '__main__':
    parser = OptionParser('Usage: %prog [options] [SERVICE ...]')
    logger_options(parser, logging.INFO)
    (options, args) = parser.parse_args()
    log = logger(options)
    if len(args) < 1:
        parser.error('No service name provided')
    for service in args:
        pidfile = pidfile_path(service)
        log.debug("PID file is %s", pidfile)
        if os.path.exists(pidfile):
            pid = open(pidfile).read()
            try:
                pid = int(pid)
            except ValueError:
                log.error("Badly formatted PID in %s (%r)", pidfile, pid)
            else:
                log.info("Killing %s (%d)", service, pid)
                try:
                    os.kill(pid, SIGTERM)
                except OSError, x:
                    log.error("Unable to kill %s (%d) - %s",
                            service, pid, x.strerror)
                try:
                    os.unlink(pidfile)
                except OSError:
                    pass
        else:
            log.debug("No PID file for %s", service)


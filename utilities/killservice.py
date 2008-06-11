#!/usr/bin/python2.4

# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# This module uses relative imports.
# pylint: disable-msg=W0403

__metaclass__ = type

import _pythonpath

import os, logging
from signal import SIGTERM
from optparse import OptionParser
from canonical.config import config
from canonical.pidfile import get_pid, pidfile_path, remove_pidfile
from canonical.launchpad.scripts import logger_options, logger
from canonical.launchpad.mailman.runmailman import stop_mailman


if __name__ == '__main__':
    parser = OptionParser('Usage: %prog [options] [SERVICE ...]')
    logger_options(parser, logging.INFO)
    (options, args) = parser.parse_args()
    log = logger(options)
    if len(args) < 1:
        parser.error('No service name provided')
    for service in args:
        # Mailman is special, but only stop it if it was launched.
        if service == 'mailman' and config.mailman.launch:
            stop_mailman()
            continue
        log.debug("PID file is %s", pidfile_path(service))
        try:
            pid = get_pid(service)
        except ValueError, error:
            log.error(error)
            continue
        if pid is not None:
            log.info("Killing %s (%d)", service, pid)
            try:
                os.kill(pid, SIGTERM)
            except OSError, x:
                log.error("Unable to kill %s (%d) - %s",
                          service, pid, x.strerror)
            try:
                remove_pidfile(service)
            except OSError:
                pass
        else:
            log.debug("No PID file for %s", service)

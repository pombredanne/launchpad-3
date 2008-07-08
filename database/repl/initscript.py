#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Start/stop/restart the slon processes."""

__metaclass__ = type
__all__ = []

import _pythonpath

from optparse import OptionParser
import subprocess
import sys

from canonical.launchpad.scripts import logger, logger_options


# These should be pulled from config
CLUSTER_NAME = 'dev'
CONNECTION_INFOS = [
    ('master', 'host=localhost user=slony dbname=launchpad_dev'),
    ('slave1', 'host=localhost user=slony dbname=launchpad_dev_slave1'),
    ]

def slon(name, connection_info):
    log = logger()
    log.info('Starting %s slon [%s]' % (name, connection_info))
    output_file = '/var/log/postgresql/slon_%s.log' % name
    command = "nohup slon -d 2 -l 3 '%s' '%s' 2>&1 >> %s &" % (
            CLUSTER_NAME, connection_info, output_file)
    log.debug('Running %s' % command)
    subprocess.call(command, shell=True)


def do_start():
    log = logger()
    for node_name, connection_info in CONNECTION_INFOS:
        slon(node_name, connection_info)


def main():
    parser = OptionParser('Usage: %prog [start | stop | restart]')
    logger_options(parser)
    options, args = parser.parse_args()
    if len(args) == 0:
        parser.error('Required argument missing')
        sys.exit(1)
    elif len(args) > 1:
        parser.error('Too many arguments')
        sys.exit(1)
    command = args[0]

    if command == 'start':
        return do_start()
    elif command == 'stop':
        return do_stop()
    elif command == 'restart':
        do_stop()
        return do_start()

    
if __name__ == '__main__':
    sys.exit(main())

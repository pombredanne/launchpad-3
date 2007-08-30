#!/usr/bin/python2.4
# Copyright 2005 Canonical Ltd.  All rights reserved.


import sys
import logging
import optparse
import MySQLdb

import _pythonpath

from zope.component import getUtility
from canonical.config import config
from canonical.lp import initZopeless
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger)
from canonical.launchpad.ftests import login

from canonical.launchpad.scripts import bugzilla


def make_connection(options):
    kws = {}
    if options.db_name is not None:
        kws['db'] = options.db_name
    if options.db_user is not None:
        kws['user'] = options.db_user
    if options.db_password is not None:
        kws['passwd'] = options.db_passwd
    if options.db_host is not None:
        kws['host'] = options.db_host

    return MySQLdb.connect(**kws)
        
def main(argv):
    parser = optparse.OptionParser(
        description="This script imports bugs from a Bugzilla into Launchpad.")

    parser.add_option('--component', metavar='COMPONENT', action='append',
                      help='Limit to this bugzilla component',
                      type='string', dest='component', default=[])
    parser.add_option('--status', metavar='STATUS,...', action='store',
                      help='Only import bugs with the given status',
                      type='string', dest='status',
                      default=None)

    # MySQL connection details
    parser.add_option('-d', '--dbname', metavar='DB', action='store',
                      help='The MySQL database name',
                      type='string', dest='db_name', default='bugs_warty')
    parser.add_option('-U', '--username', metavar='USER', action='store',
                      help='The MySQL user name',
                      type='string', dest='db_user', default=None)
    parser.add_option('-p', '--password', metavar='PASSWORD', action='store',
                      help='The MySQL password',
                      type='string', dest='db_password', default=None)
    parser.add_option('-H', '--host', metavar='HOST', action='store',
                      help='The MySQL database host',
                      type='string', dest='db_host', default=None)

    # logging options
    logger_options(parser, logging.INFO)
    
    options, args = parser.parse_args(argv[1:])
    if options.status is not None:
        options.status = options.status.split(',')
    else:
        options.status = []

    logger(options, 'canonical.launchpad.scripts.bugzilla')

    # don't send email
    config.zopeless.send_email = False
    
    ztm = initZopeless()
    execute_zcml_for_scripts()
    login('bug-importer@launchpad.net')

    db = make_connection(options)
    bz = bugzilla.Bugzilla(db)

    bz.importBugs(ztm,
                  product=['Ubuntu'],
                  component=options.component,
                  status=options.status)

    bz.processDuplicates(ztm)

if __name__ == '__main__':
    sys.exit(main(sys.argv))

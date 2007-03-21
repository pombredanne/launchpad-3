#!/usr/bin/python2.4
# Copyright 2006 Canonical Ltd.  All rights reserved.

import logging
import optparse
import sys

import _pythonpath

from zope.component import getUtility
from canonical.config import config
from canonical.lp import initZopeless
from canonical.launchpad.interfaces import IProductSet
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger)
from canonical.launchpad.ftests import login

from canonical.launchpad.scripts.bugimport import BugImporter

def main(argv):
    parser = optparse.OptionParser(
        description="Export bugs for a Launchpad product as XML")
    parser.add_option('-p', '--product', metavar='PRODUCT', action='store',
                      help='Which product to export',
                      type='string', dest='product', default=None)
    parser.add_option('--cache', metavar='FILE', action='store',
                      help='Cache for bug ID mapping',
                      type='string', dest='cache_filename',
                      default='bug-map.pickle')
    parser.add_option('--verify-users', dest='verify_users',
                      help='Should created users have verified emails?',
                      action='store_true', default=False)
    logger_options(parser, logging.INFO)

    options, args = parser.parse_args(argv[1:])
    logger(options, 'canonical.launchpad.scripts.bugimport')

    if options.product is None:
        parser.error('No product specified')
    if len(args) != 1:
        parser.error('Please specify a bug XML file to import')
    bugs_filename = args[0]

    # don't send email
    config.zopeless.send_email = False

    execute_zcml_for_scripts()
    ztm = initZopeless()
    login('bug-importer@launchpad.net')

    product = getUtility(IProductSet).getByName(options.product)
    if product is None:
        parser.error('Product %s does not exist' % options.product)

    importer = BugImporter(product, bugs_filename, options.cache_filename,
                           verify_users=options.verify_users)
    importer.importBugs(ztm)

if __name__ == '__main__':
    sys.exit(main(sys.argv))

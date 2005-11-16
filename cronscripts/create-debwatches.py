#!/usr/bin/env python

# Copyright 2005 Canonical Ltd.  All rights reserved.

# This script aims to ensure that there is a Malone watch on Debian bugs
# that meet certain criteria. The Malone watch will be linked to a BugTask
# on Debian for that bug. The business of syncing is handled separately.

__metaclass__ = type

import os
import sys
import logging
import _pythonpath
from optparse import OptionParser

# zope bits
from zope.component import getUtility

# canonical launchpad modules
from canonical.lp import initZopeless
from canonical.launchpad.scripts import (execute_zcml_for_scripts,
    logger_options, logger as logger_from_options)
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.scripts.debsync import (
    bug_filter, do_import, import_bug)
from canonical.launchpad.interfaces import ILaunchpadCelebrities


# setup core values and defaults
debbugs_location_default = '/srv/bugs-mirror.debian.org/'
debbugs_pl = '../lib/canonical/launchpad/scripts/debbugs-log.pl'

# the minimum age, in days, of a debbugs bug before we will import it
MIN_AGE = 7


def main(args):
    parser = OptionParser(description=("This script syncs debbugs from "
        "http://bugs.debian.org/ into Malone. It selects interesting "
        "bugs in debian and makes sure that there is a Malone bug for "
        "each of them. See debwatchsync for a tool that syncronises "
        "the bugs in Malone and debbugs, too."))
    logger_options(parser, logging.WARNING)
    parser.set_defaults(max=None, debbugs=debbugs_location_default)
    parser.add_option('--debbugs', action='store', type='string',
        dest='debbugs',
        help="The location of your debbugs database.")
    parser.add_option('--max', action='store', type='int', dest='max',
        help="The maximum number of bugs to create.")
    parser.add_option('--package', action='append', type='string',
        help="A list of packages for which we should import bugs.",
        dest="packages", default=[])
    options, args = parser.parse_args()

    # setup the logger
    logger = logger_from_options(options)

    # make sure the debbugs location looks sane
    if not os.path.exists(os.path.join(options.debbugs, 'index/index.db')):
        logger.error('%s is not a debbugs db.' % options.debbugs)
        return 1

    # Make sure we import any Debian bugs specified on the command line
    for arg in args:
        try:
            target_bug = int(arg)
        except ValueError:
            logger.error('%s is not a valid debian bug number.' % arg)
        target_bugs.add(target_bug)

    logger.info('Setting up utilities...')
    execute_zcml_for_scripts()

    target_bugs = set()
    target_package_set = set()
    previousimportset = set()

    logger.info('Connecting to database...')
    ztm = initZopeless(implicitBegin=False)
    ztm.begin()

    logger.info('Calculating target package set...')

    # first find all the published ubuntu packages
    ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
    for p in ubuntu.currentrelease.publishedBinaryPackages(
        component='main'):
        target_package_set.add(p.binarypackagename.name)
    # then add packages passed on the command line
    for package in options.packages:
        target_package_set.add(package)
    logger.info('%d binary packages targeted.' % len(target_package_set))

    lockfile_path = '/var/lock/launchpad-debbugs-mkwatch.lock'
    lockfile = LockFile(lockfile_path)
    try:
        lockfile.acquire()
    except OSError:
        logger.info('Lockfile %s already exists, exiting.' % lockfile_path)
        return 0

    ztm.abort()
    try:
        ztm.begin()
        do_import(logger, options.max, options.debbugs, target_bugs,
            target_package_set, previousimportset, MIN_AGE, debbugs_pl)
        ztm.commit()
    except:
        logger.exception('Uncaught exception!')
        lockfile.release()
        return 1

    logger.info('Done!')
    lockfile.release()
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))


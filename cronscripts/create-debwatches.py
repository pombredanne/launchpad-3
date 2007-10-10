#!/usr/bin/python2.4

# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

# This script aims to ensure that there is a Malone watch on Debian bugs
# that meet certain criteria. The Malone watch will be linked to a BugTask
# on Debian for that bug. The business of syncing is handled separately.

__metaclass__ = type

import os
import logging
import _pythonpath

# zope bits
from zope.component import getUtility

# canonical launchpad modules
from canonical.launchpad.scripts.debsync import (
    do_import)
from canonical.launchpad.scripts.base import (
    LaunchpadCronScript, LaunchpadScriptFailure)
from canonical.launchpad.interfaces import ILaunchpadCelebrities


# setup core values and defaults
debbugs_location_default = '/srv/bugs-mirror.debian.org/'
debbugs_pl = '../lib/canonical/launchpad/scripts/debbugs-log.pl'

# the minimum age, in days, of a debbugs bug before we will import it
MIN_AGE = 7


class CreateDebWatches(LaunchpadCronScript):
    description = """
    This script syncs debbugs from http://bugs.debian.org/ into Malone.
    It selects interesting bugs in debian and makes sure that there is a
    Malone bug for each of them. See debwatchsync for a tool that
    syncronises the bugs in Malone and debbugs, too.
    """
    loglevel = logging.WARNING
    def add_my_options(self):
        self.parser.set_defaults(max=None, debbugs=debbugs_location_default)
        self.parser.add_option('--debbugs', action='store', type='string',
            dest='debbugs',
            help="The location of your debbugs database.")
        self.parser.add_option('--max', action='store', type='int', dest='max',
            help="The maximum number of bugs to create.")
        self.parser.add_option('--package', action='append', type='string',
            help="A list of packages for which we should import bugs.",
            dest="packages", default=[])

    def main(self):
        if not os.path.exists(os.path.join(self.options.debbugs, 'index/index.db')):
            # make sure the debbugs location looks sane
            raise LaunchpadScriptFailure('%s is not a debbugs db.'
                                         % self.options.debbugs)

        # Make sure we import any Debian bugs specified on the command line
        target_bugs = set()
        for arg in self.args:
            try:
                target_bug = int(arg)
            except ValueError:
                self.logger.error('%s is not a valid debian bug number.' % arg)
            target_bugs.add(target_bug)

        target_package_set = set()
        previousimportset = set()

        self.logger.info('Calculating target package set...')

        # first find all the published ubuntu packages
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        for p in ubuntu.currentrelease.publishedBinaryPackages(
            component='main'):
            target_package_set.add(p.binarypackagename.name)
        # then add packages passed on the command line
        for package in self.options.packages:
            target_package_set.add(package)
        self.logger.info('%d binary packages targeted.' % len(target_package_set))

        self.txn.abort()
        self.txn.begin()
        do_import(self.logger, self.options.max, self.options.debbugs,
            target_bugs, target_package_set, previousimportset, MIN_AGE,
            debbugs_pl)
        self.txn.commit()

        self.logger.info('Done!')

if __name__ == '__main__':
    script = CreateDebWatches("debbugs-mkwatch")
    script.lock_and_run()


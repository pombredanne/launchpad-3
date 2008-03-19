#!/usr/bin/python2.4
# pylint: disable-msg=W0403
# Copyright 2008 Canonical Ltd.  All rights reserved.
#
# Migrate old KDE-style POTemplates to use native Launchpad
# context and plural forms support.
#
# See https://bugs.launchpad.net/rosetta/+bug/196106.
import sys
import logging

import _pythonpath

from canonical.launchpad.scripts.base import LaunchpadScript
from canonical.launchpad.scripts.migrate_kde_potemplates import (
    migrate_potemplates)

class MigrateKDEPOTemplatesScript(LaunchpadScript):

    description = ("Use native support for message context and "
                   "plural forms for legacy KDE PO templates.")
    usage = "usage: %s" % sys.argv[0]
    loglevel = logging.INFO

    def main(self):
        migrate_potemplates(self.txn, self.logger)

if __name__ == '__main__':
    script = MigrateKDEPOTemplatesScript(
        'canonical.launchpad.scripts.migrate_kde_potemplates')
    script.run()

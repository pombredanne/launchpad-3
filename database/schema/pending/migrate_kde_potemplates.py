#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
#
# pylint: disable-msg=W0403
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

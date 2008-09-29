#!/usr/bin/python2.4
# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403

"""Cronscript to prune old and unreferenced OOPS reports from the archive."""

__metaclass__ = type

import _pythonpath
import os

from canonical.config import config
from canonical.database.sqlbase import ISOLATION_LEVEL_AUTOCOMMIT
from canonical.launchpad.scripts.base import (
    LaunchpadCronScript, LaunchpadScriptFailure)
from canonical.launchpad.scripts.oops import (
    unwanted_oops_files, prune_empty_oops_directories)


default_lock_filename = '/var/lock/oops-prune.lock'

class OOPSPruner(LaunchpadCronScript):
    def add_my_options(self):
        self.parser.add_option(
                '-n', '--dry-run', default=False, action='store_true',
                dest="dry_run", help="Do a test run. No files are removed."
                )

    def main(self):
        # Default to using the OOPS directory in config file.
        if not self.args:
            self.args = [config.error_reports.error_dir]

        oops_directories = []
        for oops_dir in self.args:
            if not os.path.isdir(oops_dir):
                raise LaunchpadScriptFailure(
                    "%s is not a directory" % oops_dir)

            oops_directories.append(oops_dir)

        self.txn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        for oops_directory in oops_directories:
            for oops_path in unwanted_oops_files(oops_directory,
                                                 40, self.logger):
                self.logger.info("Removing %s", oops_path)
                if not self.options.dry_run:
                    os.unlink(oops_path)

            prune_empty_oops_directories(oops_directory)


if __name__ == '__main__':
    script = OOPSPruner('oops-prune', dbuser='oopsprune')
    script.lock_and_run()


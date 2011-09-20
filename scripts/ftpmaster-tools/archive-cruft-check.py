#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403

"""Archive Cruft checker.

A kind of archive garbage collector, supersede NBS binaries (not build
from source).
"""

import _pythonpath

from canonical.config import config
from lp.services.scripts.base import LaunchpadScript, LaunchpadScriptFailure
from lp.soyuz.scripts.ftpmaster import (
    ArchiveCruftChecker, ArchiveCruftCheckerError)


class ArchiveCruftCheckerScript(LaunchpadScript):

    usage = "Usage: archive-cruft-check.py [options] <ARCHIVE_PATH>"

    def add_my_options(self):
        self.parser.add_option(
            "-d", "--distro", dest="distro", help="remove from DISTRO")
        self.parser.add_option(
            "-n", "--no-action", dest="action", default=True,
            action="store_false", help="don't do anything")
        self.parser.add_option(
            "-s", "--suite", dest="suite", help="only act on SUITE")

    def main(self):
        if len(self.args) != 1:
            self.parser.error('ARCHIVEPATH is require')
        archive_path = self.args[0]

        checker = ArchiveCruftChecker(
            self.logger, distribution_name=self.options.distro,
            suite=self.options.suite, archive_path=archive_path)

        try:
            checker.initialize()
        except ArchiveCruftCheckerError, info:
            raise LaunchpadScriptFailure(info)

        # XXX cprov 2007-06-26 bug=121784: Disabling by distro-team request.
        #    if checker.nbs_to_remove and options.action:
        #        checker.doRemovals()
        #        ztm.commit()

if __name__ == '__main__':
    ArchiveCruftCheckerScript(
        'archive-cruft-check', config.archivepublisher.dbuser).lock_and_run()

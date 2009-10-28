#!/usr/bin/python2.4
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import _pythonpath

from lp.codehosting.branchdistro import DistroBrancher
from lp.codehosting.vfs import get_multi_server
from lp.services.scripts.base import LaunchpadScript, LaunchpadScriptFailure


class BranchDistroScript(LaunchpadScript):

    usage = "%prog distro old-series new-series"

    def add_my_options(self):
        self.parser.add_option(
            '--check', dest="check", action="store_true", default=False,
            help=("Check that the new distro series has its official "
                  "branches set up correctly."))

    def main(self):
        if len(self.args) != 3:
            self.parser.error("Wrong number of arguments.")
        brancher = DistroBrancher.fromNames(self.logger, *self.args)
        server = get_multi_server(
            write_mirrored=True, write_hosted=True, direct_database=True)
        server.setUp()
        try:
            if self.options.check:
                if not brancher.checkNewBranches():
                    raise LaunchpadScriptFailure("Check failed")
            else:
                brancher.makeNewBranches()
        finally:
            server.tearDown()

if __name__ == '__main__':
    BranchDistroScript("branch-distro", dbuser='branch-distro').run()

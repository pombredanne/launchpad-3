#!/usr/bin/python2.4
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import _pythonpath

from lp.codehosting.branch_distro import branch_distro
from lp.services.scripts.base import LaunchpadScript


class BranchDistroScript(LaunchpadScript):
    usage = "%prog distro old-series new-series"
    def main(self):
        if len(self.args) != 3:
            self.parser.error("Wrong number of arguments.")
        branch_distro(self.logger, *self.args)

if __name__ == '__main__':
    BranchDistroScript("branch-distro", dbuser='branch-distro').run()

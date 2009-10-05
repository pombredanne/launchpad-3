#/usr/bin/python2.4
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import _pythonpath

from lp.codehosting.branch_ubuntu import branch_ubuntu
from lp.services.scripts.base import LaunchpadScript


class BranchUbuntuScript(LaunchpadScript):
    def main(self):
        branch_ubuntu()

if __name__ == '__main__':
    BranchUbuntuScript("branch-ubuntu", dbuser='branch-ubuntu').run()

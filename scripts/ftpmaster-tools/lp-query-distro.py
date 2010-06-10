#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403
"""It provides easy integration of other scripts without database access.

   It should provide an easy way to retrieve current information from
   Launchpad when using plain shell scripts, for example:

   * CURRENT distroseries name: `./ubuntu-helper.py -d ubuntu current`
   * DEVELOPMENT distroseries name:
       `./ubuntu-helper.py -d ubuntu development`
   * Distorelease architectures:
       `./lp-query-distro.py -d ubuntu -s feisty archs`
   * Distorelease official architectures:
       `./lp-query-distro.py -d ubuntu -s feisty official_archs`
   * Distorelease nominated-arch-indep:
       `./lp-query-distro.py -d ubuntu -s feisty nominated_arch_indep`

   Standard Output will carry the successfully executed information and
   exit_code will be ZERO.
   In case of failure, exit_code will be different than ZERO and Standard
   Error will contain debug information.
   """

import _pythonpath

from lp.soyuz.scripts.ftpmaster import LpQueryDistro


if __name__ == '__main__':
    script = LpQueryDistro('lp-query-distro', dbuser='ro')
    script.run()

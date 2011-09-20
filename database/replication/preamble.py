#!/usr/bin/python -S
#
# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Generate a preamble for slonik(1) scripts based on the current LPCONFIG.
"""

__metaclass__ = type
__all__ = []

from optparse import OptionParser
import time

import _pythonpath
import replication.helpers

from canonical.config import config
from canonical.database.sqlbase import connect
from canonical.launchpad import scripts


if __name__ == '__main__':
    parser = OptionParser()
    scripts.db_options(parser)
    (options, args) = parser.parse_args()
    if args:
        parser.error("Too many arguments")
    scripts.execute_zcml_for_scripts(use_web_security=False)

    con = connect()
    print '# slonik(1) preamble generated %s' % time.ctime()
    print '# LPCONFIG=%s' % config.instance_name
    print
    print replication.helpers.preamble(con)

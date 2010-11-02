#!/usr/bin/python -S
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Calculate database replication lag and cache it."""

__metaclass__ = type
__all__ = []

import _pythonpath

import sys
import time

import psycopg2

from canonical.database.sqlbase import connect, ISOLATION_LEVEL_AUTOCOMMIT
from canonical.launchpad.scripts import db_options, logger
from lp.scripts.helpers import LPOptionParser


def main(args=None):
    parser = LPOptionParser()
    db_options(parser)
    parser.add_option(
        "-s", "--sleep", dest="sleep", type="int", default=5,
        metavar="SECS", help="Wait SECS seconds between refreshes.")

    (options, args) = parser.parse_args(args)
    if len(args) != 0:
        parser.error("Too many arguments.")

    log = logger(options)

    while True:
        try:
            con = connect(user="lagmon", isolation=ISOLATION_LEVEL_AUTOCOMMIT)
            cur = con.cursor()
            while True:
                cur.execute("SELECT update_replication_lag_cache()")
                if cur.fetchone()[0]:
                    log.info("Updated.")
                else:
                    log.error("update_replication_lag_cache() failed.")
                time.sleep(options.sleep)
        except psycopg2.Error, x:
            log.error("%s. Retrying.", str(x).strip())
            time.sleep(options.sleep)


if __name__ == '__main__':
    sys.exit(main())

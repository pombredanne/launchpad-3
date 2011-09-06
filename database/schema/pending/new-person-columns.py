#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Populate some new columns on the Person table."""

__metaclass__ = type
__all__ = []

import _pythonpath

from optparse import OptionParser

from canonical.database.sqlbase import connect, ISOLATION_LEVEL_AUTOCOMMIT
from canonical.launchpad.scripts import db_options
from canonical.launchpad.scripts.logger import log, logger_options


def update_until_done(con, table, query, vacuum_every=100):
    log.info("Running %s" % query)
    loops = 0
    total_rows = 0
    cur = con.cursor()
    while True:
        loops += 1
        cur.execute(query)
        rowcount = cur.rowcount
        total_rows += rowcount
        log.debug("Updated %d" % total_rows)
        if loops % vacuum_every == 0:
            log.debug("Vacuuming %s" % table)
            cur.execute("VACUUM %s" % table)
        if rowcount <= 0:
            log.info("Done")
            return

parser = OptionParser()
logger_options(parser)
db_options(parser)
options, args = parser.parse_args()

con = connect(isolation=ISOLATION_LEVEL_AUTOCOMMIT)

update_until_done(con, 'person', """
    UPDATE Person
    SET
        verbose_bugnotifications = FALSE,
        visibility = COALESCE(visibility, 1)
    WHERE id IN (
        SELECT Person.id
        FROM Person
        WHERE visibility IS NULL OR verbose_bugnotifications IS NULL
        LIMIT 200
        )
    """)

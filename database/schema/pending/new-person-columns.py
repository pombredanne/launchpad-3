#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Populate some new columns on the Person table."""

__metaclass__ = type
__all__ = []

import _pythonpath

from optparse import OptionParser
import sys

from canonical.database.sqlbase import connect, AUTOCOMMIT_ISOLATION
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

con = connect(options.dbuser, isolation=AUTOCOMMIT_ISOLATION)

# Valid people not teams
update_until_done(con, 'person', """
    UPDATE Person
    SET
        account_status = 20, personal_standing = 0,
        mailing_list_receive_duplicates = TRUE,
        mailing_list_auto_subscribe_policy = 1
    WHERE id IN (
        SELECT Person.id
        FROM Person, ValidPersonOrTeamCache
        WHERE teamowner IS NULL
            AND Person.id = ValidPersonOrTeamCache.id
            AND account_status IS NULL
        LIMIT 200
        )
    """)

# Everyone else
update_until_done(con, 'person', """
    UPDATE Person
    SET
        account_status = 10, personal_standing = 0,
        mailing_list_receive_duplicates = TRUE,
        mailing_list_auto_subscribe_policy = 1
    WHERE id IN (
        SELECT id FROM Person WHERE account_status IS NULL
        LIMIT 200
        )
    """)

cur = con.cursor()
cur.execute("SELECT count(*) from Person where account_status IS NULL")
rows = cur.fetchone()[0]
if rows == 0:
    print 'Everything updated'
else:
    print 'Rows where missed!'
    sys.exit(1)

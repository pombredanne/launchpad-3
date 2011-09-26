#!/usr/bin/python -S
#
# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Prune old nonces."""

__metaclass__ = type
__all__ = []

from optparse import OptionParser

import _pythonpath

from canonical.database.sqlbase import (
    connect,
    ISOLATION_LEVEL_AUTOCOMMIT,
    )
from canonical.launchpad.scripts import db_options
from canonical.launchpad.scripts.logger import (
    log,
    logger_options,
    )


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
        if vacuum_every is not None and loops % vacuum_every == 0:
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

update_until_done(con, 'OAuthNonce', """
    DELETE FROM OAuthNonce
    WHERE id IN (
        SELECT id FROM OAuthNonce
        WHERE request_timestamp < 'yesterday'
        LIMIT 5000)
    """, vacuum_every=None)

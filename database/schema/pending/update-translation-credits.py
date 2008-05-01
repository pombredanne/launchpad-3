#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Populate some new columns on the Person table."""

__metaclass__ = type
__all__ = []

import _pythonpath

from optparse import OptionParser
import sys

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

con = connect(options.dbuser, isolation=ISOLATION_LEVEL_AUTOCOMMIT)

#  People have so far updated translation credits, often mis-crediting people,
#  or removing credits to upstream translators: we want to disable all of these
#  translation, so automatic handling will pick up from now on.
update_until_done(con, 'posubmission', """
    UPDATE posubmission SET active=FALSE WHERE id IN (
        SELECT posubmission.id
        FROM posubmission,
             pomsgset,
             potmsgset,
             pomsgid
        WHERE
            posubmission.active IS TRUE AND
            posubmission.pomsgset=pomsgset.id AND 
            potmsgset=potmsgset.id AND
            primemsgid=pomsgid.id AND
            published IS NOT TRUE AND
            (msgid='translation-credits' OR
             msgid='translator-credits' OR
             msgid='translator_credits' OR
             msgid=E'_: EMAIL OF TRANSLATORS\nYour emails' OR
             msgid=E'_: NAME OF TRANSLATORS\nYour names')
        LIMIT 200
        )
    """)

# Set any existing inactive published translations as active
update_until_done(con, 'posubmission', """
    UPDATE posubmission SET active=TRUE WHERE id IN (
        SELECT posubmission.id
        FROM posubmission,
             pomsgset,
             potmsgset,
             pomsgid
        WHERE
            posubmission.active IS FALSE AND
            posubmission.pomsgset=pomsgset.id AND 
            pomsgset.potmsgset=potmsgset.id AND
            potmsgset.primemsgid=pomsgid.id AND
            posubmission.published IS TRUE AND
            (msgid='translation-credits' OR
             msgid='translator-credits' OR
             msgid='translator_credits' OR
             msgid=E'_: EMAIL OF TRANSLATORS\nYour emails' OR
             msgid=E'_: NAME OF TRANSLATORS\nYour names')
        LIMIT 200
        )
    """)

# Remove reviewer, date_reviewed from all translation credit POMsgSets
update_until_done(con, 'pomsgset', """
    UPDATE POMsgSet SET reviewer=NULL, date_reviewed=NULL
    WHERE id IN (
        SELECT POMsgSet.id
        FROM POMsgSet, POTMsgSet, POMsgId
        WHERE
            POMsgSet.reviewer IS NOT NULL AND
            POMsgSet.potmsgset=POTMsgSet.id AND
            POTMsgSet.primemsgid=POMsgId.id AND
            (msgid='translation-credits' OR
            msgid='translator-credits' OR
            msgid='translator_credits' OR
            msgid=E'_: EMAIL OF TRANSLATORS\nYour emails' OR
            msgid=E'_: NAME OF TRANSLATORS\nYour names')
        LIMIT 200
        )
    """)


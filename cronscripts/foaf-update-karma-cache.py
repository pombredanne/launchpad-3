#!/usr/bin/env python
# Copyright 2005 Canonical Ltd.  All rights reserved.

import _pythonpath

import sys
from optparse import OptionParser

from zope.component import getUtility

from canonical.config import config
from canonical.lp import initZopeless, AUTOCOMMIT_ISOLATION
from canonical.launchpad.scripts import (
        execute_zcml_for_scripts, logger_options, logger
        )
from canonical.launchpad.scripts.lockfile import LockFile
from canonical.launchpad.interfaces import IPersonSet
from canonical.database.sqlbase import cursor

_default_lock_file = '/var/lock/launchpad-karma-update.lock'


def update_karma_cache():
    """Update the KarmaCache table for all valid Launchpad users.

    For each Launchpad user with a preferred email address, calculate his
    karmavalue for each category of actions we have and update his entry in
    the KarmaCache table. If a user doesn't have an entry for that category in
    KarmaCache a new one will be created.
    """
    ztm = initZopeless(
            dbuser=config.karmacacheupdater.dbuser,
            implicitBegin=False, isolation=AUTOCOMMIT_ISOLATION
            )
    ztm.begin()
    cur = cursor()
    karma_expires_after = '1 year'
    
    # Calculate everyones karma. Karma degrades each day, becoming
    # worthless after karma_expires_after. This query produces odd results
    # when datecreated is in the future, but there is really no point adding
    # the extra WHEN clause.
    log.info("Calculating everyones karma")
    cur.execute("""
        SELECT person, category, ROUND(SUM(
            CASE WHEN datecreated + %(karma_expires_after)s::interval
                <= CURRENT_TIMESTAMP AT TIME ZONE 'UTC' THEN 0
            ELSE points * (1 - extract(
                EPOCH FROM CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - datecreated
                ) / extract(EPOCH FROM %(karma_expires_after)s::interval))
            END
            ))
        FROM Karma, KarmaAction
        WHERE action = KarmaAction.id
        GROUP BY person, category
        """, vars())

    # Suck into RAM to avoid tieing up resources on the DB.
    results = list(cur.fetchall())

    log.info("Got %d (person, category) scores", len(results))

    # Note that we don't need to commit each iteration because we are running
    # in autocommit mode.
    for person, category, points in results:
        log.debug(
            "Setting person=%(person)d, category=%(category)d, "
            "points=%(points)d", vars()
            )
        cur.execute("""
            UPDATE KarmaCache SET karmavalue=%(points)s
            WHERE person=%(person)s AND category=%(category)s
            """, vars())
        assert cur.rowcount in (0, 1), \
                'Bad rowcount %r returned from DML' % (cur.rowcount,)
        if cur.rowcount == 0:
            cur.execute("""
                INSERT INTO KarmaCache (person, category, karmavalue)
                VALUES (%(person)s, %(category)s, %(points)s)
                """, vars())

    # Update the KarmaTotalCache table
    cur.execute("BEGIN")
    log.info("Rebuilding KarmaTotalCache")
    cur.execute("DELETE FROM KarmaTotalCache")
    cur.execute("""
        INSERT INTO KarmaTotalCache (person, karma_total)
        SELECT person, SUM(karmavalue) FROM KarmaCache
        GROUP BY person
        """)
    cur.execute("COMMIT")

if __name__ == '__main__':
    parser = OptionParser()
    logger_options(parser)
    (options, arguments) = parser.parse_args()
    if arguments:
        parser.error("Unhandled arguments %s" % repr(arguments))
    execute_zcml_for_scripts()

    log = logger(options, 'karmacache')
    log.info("Updating the karma cache of Launchpad users.")

    lockfile = LockFile(_default_lock_file, logger=log)
    try:
        lockfile.acquire()
    except OSError:
        log.info("lockfile %s already exists, exiting", _default_lock_file)
        sys.exit(1)

    try:
        update_karma_cache()
    finally:
        lockfile.release()

    log.info("Finished updating the karma cache of Launchpad users.")


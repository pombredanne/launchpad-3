#!/usr/bin/env python
# Copyright 2005-2006 Canonical Ltd.  All rights reserved.

import _pythonpath

import sys
from optparse import OptionParser

from contrib.glock import GlobalLock, LockAlreadyAcquired

from zope.component import getUtility

from canonical.config import config
from canonical.lp import initZopeless, AUTOCOMMIT_ISOLATION
from canonical.launchpad.scripts import (
        execute_zcml_for_scripts, logger_options, logger
        )
from canonical.launchpad.interfaces import IKarmaCacheManager, NotFoundError
from canonical.database.sqlbase import cursor

_default_lock_file = '/var/lock/launchpad-karma-update.lock'

def update_karma_cache():
    """Update the KarmaCache table for all valid Launchpad users.

    For each Launchpad user with a preferred email address, calculate his
    karmavalue for each category of actions we have and update his entry in
    the KarmaCache table. If a user doesn't have an entry for that category in
    KarmaCache a new one will be created.
    """
    # We use the autocommit transaction isolation level to minimize
    # contention, and also allows us to not bother explicitly calling
    # COMMIT all the time. This script in no way relies on transactions,
    # so it is safe.
    ztm = initZopeless(
        dbuser=config.karmacacheupdater.dbuser, implicitBegin=True,
        isolation=AUTOCOMMIT_ISOLATION)
    cur = cursor()
    karma_expires_after = '1 year'

    karmacachemanager = getUtility(IKarmaCacheManager)

    # Calculate everyones karma. Karma degrades each day, becoming
    # worthless after karma_expires_after. This query produces odd results
    # when datecreated is in the future, but there is really no point adding
    # the extra WHEN clause.
    log.info("Calculating everyones karma")
    cur.execute("""
        SELECT person, category, product, distribution, Product.project,
            ROUND(SUM(
            CASE WHEN karma.datecreated + %(karma_expires_after)s::interval
                <= CURRENT_TIMESTAMP AT TIME ZONE 'UTC' THEN 0
            ELSE points * (1 - extract(
                EPOCH FROM CURRENT_TIMESTAMP AT TIME ZONE 'UTC' -
                karma.datecreated
                ) / extract(EPOCH FROM %(karma_expires_after)s::interval))
            END
            ))
        FROM Karma
        JOIN KarmaAction ON action = KarmaAction.id
        LEFT JOIN Product ON product = Product.id
        GROUP BY person, category, product, distribution, Product.project
        """, vars())

    # Suck into RAM to avoid tieing up resources on the DB.
    results = list(cur.fetchall())

    log.info("Got %d (person, category) scores", len(results))

    # Get a list of categories, which we will need shortly.
    categories = {}
    cur.execute("SELECT id, name from KarmaCategory")
    for id, name in cur.fetchall():
        categories[id] = name

    # Calculate normalization factor for each category. We currently have
    # category bloat, where translators dominate the top karma rankings.
    # By calculating a scaling factor automatically, this slant will be
    # removed even as more events are added or scoring tweaked.
    totals = {} # Total points per category
    for dummy, category, dummy, dummy, dummy, points in results:
        if category in totals:
            totals[category] += points
        else:
            totals[category] = points
    largest_total = max(totals.values())
    scaling = {} # Scaling factor to apply per category
    for category, total in totals.items():
        if total != 0:
            scaling[category] = float(largest_total) / float(total)
        else:
            scaling[category] = 1
        log.info('Scaling %s by a factor of %0.4f' % (
            categories[category], scaling[category]
            ))
        max_scaling = config.karmacacheupdater.max_scaling
        if scaling[category] > max_scaling:
            scaling[category] = max_scaling
            log.info('Reducing %s scaling to %d to avoid spikes' % (
                categories[category], max_scaling
                ))

    # Note that we don't need to commit each iteration because we are running
    # in autocommit mode.
    for (person_id, category_id, product_id, distribution_id,
         project_id, points) in results:
        points *= scaling[category_id] # Scaled
        log.debug(
            "Setting person_id=%(person_id)d, category_id=%(category_id)d, "
            "points=%(points)d", vars()
            )

        points = int(points)
        context = {'product_id': product_id,
                   'project_id': project_id,
                   'distribution_id': distribution_id}
        try:
            # Try to update
            karmacachemanager.updateKarmaValue(
                points, person_id, category_id, **context)
            log.debug("Updated karmacache for person=%s, points=%s, "
                      "category=%s, context=%s"
                      % (person_id, points, category_id, context))
        except NotFoundError:
            # Row didn't exist; do an insert.
            karmacachemanager.new(
                points, person_id, category_id, **context)
            log.debug("Created karmacache for person=%s, points=%s, "
                      "category=%s, context=%s"
                      % (person_id, points, category_id, context))

    # Delete the entries we're going to replace.
    cur.execute("DELETE FROM KarmaCache WHERE category IS NULL")
    # XXX: It may also be necessary to delete all entries with a project !=
    # NULL and a product == NULL, since these are other calculated values.
    # We need to do this before calculating the total caches.

    # Don't allow our table to bloat with inactive users
    cur.execute("DELETE FROM KarmaCache WHERE karmavalue <= 0")

    # VACUUM KarmaCache since we have just touched every record in it
    cur.execute("""VACUUM KarmaCache""")

    # Update the KarmaTotalCache table
    log.info("Rebuilding KarmaTotalCache")
    # Trash old records
    cur.execute("""
        DELETE FROM KarmaTotalCache
        WHERE person NOT IN (SELECT person FROM KarmaCache)
        """)
    # Update existing records
    cur.execute("""
        UPDATE KarmaTotalCache SET karma_total=sum_karmavalue
        FROM (
            SELECT person AS sum_person, SUM(karmavalue) AS sum_karmavalue
            FROM KarmaCache
            GROUP BY person
            ) AS sums
        WHERE KarmaTotalCache.person = sum_person
        """)

    # VACUUM KarmaTotalCache since we have just touched every row in it.
    cur.execute("""VACUUM KarmaTotalCache""")

    # Insert new records into the KarmaTotalCache table. If deadlocks
    # become a problem, first LOCK the corresponding rows in the Person table
    # so the bulk insert cannot fail. We don't bother at the moment as this
    # would involve granting UPDATE rights on the Person table to the
    # karmacacheupdater user.
    ## cur.execute("BEGIN")
    ## cur.execute("""
    ##     SELECT * FROM Person
    ##     WHERE id NOT IN (SELECT person FROM KarmaTotalCache)
    ##     FOR UPDATE
    ##     """)
    cur.execute("""
        INSERT INTO KarmaTotalCache (person, karma_total)
        SELECT person, SUM(karmavalue) FROM KarmaCache
        WHERE person NOT IN (SELECT person FROM KarmaTotalCache)
        GROUP BY person
        """)
    ## cur.execute("COMMIT")

    # Now we must issue some SUM queries to insert the karma totals for: 
    # - All actions of a person on a given product
    # - All actions of a person on a given distribution
    # - All actions of a person on a given project
    # - All actions with a specific category of a person on a given project

    # XXX: This is done as the last step because we don't want to include
    # these values in our calculation of KarmaTotalCache

    # - All actions of a person on a given product
    cur.execute("""
        INSERT INTO KarmaCache 
            (person, category, karmavalue, product, distribution,
             sourcepackagename, project)
        SELECT person, NULL, SUM(karmavalue), product, NULL, NULL, NULL
        FROM KarmaCache
        WHERE product IS NOT NULL
        GROUP BY person, product
        """)

    # - All actions of a person on a given distribution
    cur.execute("""
        INSERT INTO KarmaCache 
            (person, category, karmavalue, product, distribution,
             sourcepackagename, project)
        SELECT person, NULL, SUM(karmavalue), NULL, distribution, NULL, NULL
        FROM KarmaCache
        WHERE distribution IS NOT NULL
        GROUP BY person, distribution
        """)

    # - All actions of a person on a given project
    cur.execute("""
        INSERT INTO KarmaCache 
            (person, category, karmavalue, product, distribution,
             sourcepackagename, project)
        SELECT person, NULL, SUM(karmavalue), NULL, NULL, NULL, project
        FROM KarmaCache
        WHERE project IS NOT NULL
        GROUP BY person, project
        """)

    # - All actions with a specific category of a person on a given project
    # XXX: This has to be the latest step; otherwise the rows inserted here
    # will be included in the calculation of the overall karma of a person on
    # a given project.
    cur.execute("""
        INSERT INTO KarmaCache 
            (person, category, karmavalue, product, distribution,
             sourcepackagename, project)
        SELECT person, category, SUM(karmavalue), NULL, NULL, NULL, project
        FROM KarmaCache
        WHERE project IS NOT NULL
            AND category IS NOT NULL
        GROUP BY person, category, project
        """)


if __name__ == '__main__':
    parser = OptionParser()
    logger_options(parser)
    (options, arguments) = parser.parse_args()
    if arguments:
        parser.error("Unhandled arguments %s" % repr(arguments))

    execute_zcml_for_scripts()

    log = logger(options, 'karmacache')
    log.info("Updating the karma cache of Launchpad users.")

    lockfile = GlobalLock(_default_lock_file, logger=log)
    try:
        lockfile.acquire()
    except LockAlreadyAcquired:
        log.error("lockfile %s already exists, exiting", _default_lock_file)
        sys.exit(1)

    try:
        update_karma_cache()
    finally:
        lockfile.release()

    log.info("Finished updating the karma cache of Launchpad users.")


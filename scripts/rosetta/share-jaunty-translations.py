#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403
# (Suppressing pylint "relative import" warning 0403 for _pythonpath)

import _pythonpath

from zope.interface import implements

from canonical.database.postgresql import drop_tables
from canonical.database.sqlbase import (
    cursor, quote, quote_identifier, sqlvalues)
from canonical.launchpad.interfaces.looptuner import ITunableLoop
from lp.services.scripts.base import LaunchpadScript
from canonical.launchpad.utilities.looptuner import DBLoopTuner


class ShareJauntyTranslationMessages:
    """`ITunableLoop` to share Jaunty TranslationMessages."""

    implements(ITunableLoop)
    def __init__(self, txn, logger, flag, seriesname):
        self.txn = txn
        self.logger = logger
        self.last_id = 0

        cur = cursor()

        cur.execute("""
            SELECT DistroSeries.id
            FROM DistroSeries
            JOIN Distribution ON Distribution.id = DistroSeries.distribution
            WHERE
                Distribution.name = 'ubuntu' AND DistroSeries.name = %s
            """ % quote(seriesname))
        self.series_id = cur.fetchone()

        substitutions = {
            'flag': quote_identifier(flag),
            'series_id': quote(self.series_id),
        }

        cur.execute("""
            SELECT DISTINCT Candidate.id
            INTO TEMP TABLE temp_todo
            FROM TranslationMessage Candidate
            JOIN POTemplate ON Candidate.potemplate = POTemplate.id
            LEFT JOIN TranslationMessage AS FlagHolder ON
                FlagHolder.%(flag)s IS TRUE AND
                FlagHolder.potmsgset = Candidate.potmsgset AND
                FlagHolder.potemplate IS NULL AND
                FlagHolder.language = Candidate.language
            WHERE
                POTemplate.distroseries = %(series_id)s AND
                POTemplate.iscurrent IS TRUE AND
                Candidate.%(flag)s IS TRUE AND
                FlagHolder.id IS NULL
            ORDER BY id
            """ % substitutions)

        cur.execute(
            "CREATE UNIQUE INDEX temp_todo__pkey ON temp_todo(id)")
        cur.execute("ANALYZE temp_todo(id)")

        cur.execute("SELECT max(id) FROM temp_todo")
        max_id, = cur.fetchone()
        if max_id is None:
            self.finish_id = 0
        else:
            self.finish_id = max_id + 1

    def isDone(self):
        """See `ITunableLoop`."""
        done = (self.last_id >= self.finish_id)
        if done:
            drop_tables(cursor(), 'temp_todo')
        return done

    def __call__(self, chunk_size):
        """See `ITunableLoop`."""
        chunk_size = int(chunk_size)

        cur = cursor()
        cur.execute("""
            SELECT id
            FROM temp_todo
            WHERE id >= %s
            ORDER BY id
            OFFSET %s
            LIMIT 1
            """ % sqlvalues(self.last_id, chunk_size))
        batch_limit = cur.fetchone()
        if batch_limit is None:
            end_id = self.finish_id
        else:
            end_id, = batch_limit

        cur.execute("""
            UPDATE TranslationMessage
            SET potemplate = NULL
            WHERE id IN (
                SELECT id
                FROM temp_todo
                WHERE id >= %s AND id < %s
                )
            """ % sqlvalues(self.last_id, end_id))
        self.logger.info(
            "Updated %d rows: %d - %d." % (
                cur.rowcount, self.last_id, end_id))
        self.txn.commit()
        self.txn.begin()
        self.last_id = end_id


class ShareJauntyTranslationsScript(LaunchpadScript):

    def main(self):
        series = 'jaunty'
        self.logger.info("Making '%s' TranslationMessages shared." % series)

        for flag in ('is_current', 'is_imported'):
            self.logger.info("Sharing %s messages." % flag)
            loop = ShareJauntyTranslationMessages(
                self.txn, self.logger, flag, series)
            DBLoopTuner(loop, 5, log=self.logger).run()


if __name__ == '__main__':
    script = ShareJauntyTranslationsScript(
        'rosetta.scripts.share-jaunty-translations')
    script.run()

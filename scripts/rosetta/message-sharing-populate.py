#! /usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

"""Populate schema additions for Translations Message Sharing.

This fills three new `TranslationMessage` columns: potemplate, language,
and variant.  It also creates linking table entries connecting the
existing `POTMsgSet`s to their `POTemplate`s.

Since the schema additions are not in use yet, this script doesn't need
to be careful about grouping by template, preserving any kind of order,
and so on.

On the other hand, the Python code tree should already be initializing
the new columns and the linking table by the time this script is run.
So we do have to be careful not to interfere with that, or stumble when
some records have already been initialized properly.
"""

import _pythonpath

from zope.interface import implements

from canonical.database.postgresql import drop_tables
from canonical.database.sqlbase import cursor, sqlvalues
from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.scripts.base import LaunchpadScript
from canonical.launchpad.utilities.looptuner import DBLoopTuner


class PopulateTranslationMessage:
    """`ITunableLoop` to populate new TranslationMessage columns."""

    implements(ITunableLoop)
    def __init__(self, txn, logger):
        self.txn = txn
        self.logger = logger
        self.last_id = 0

        cur = cursor()
        cur.execute("""
            SELECT id
            INTO TEMP TABLE temp_todo
            FROM TranslationMessage
            WHERE potemplate IS NULL
            ORDER BY id
            """)
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
            UPDATE TranslationMessage AS Msg
            SET
                potemplate = POFile.potemplate,
                language = POFile.language,
                variant = POFile.variant
            FROM POFile
            WHERE
                POFile.id = Msg.pofile AND
                Msg.potemplate IS NULL AND
                Msg.id IN (
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


class PopulateTranslationTemplateItem:
    """`ITunableLoop` to populate TranslationTemplateItem linking table."""

    implements(ITunableLoop)
    def __init__(self, txn, logger):
        self.txn = txn
        self.done = False
        self.logger = logger
        self.last_id = 0

        cur = cursor()
        cur.execute("""
            SELECT POTMsgSet.id
            INTO TEMP TABLE temp_todo
            FROM POTMsgSet
            LEFT JOIN TranslationTemplateItem AS ExistingEntry ON
                ExistingEntry.potmsgset = potmsgset.id
            WHERE
                POTMsgSet.sequence > 0 AND
                ExistingEntry.id IS NULL
            ORDER BY id
            """)
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
            INSERT INTO TranslationTemplateItem(
                potemplate, sequence, potmsgset)
            SELECT POTMsgSet.potemplate, POTMsgSet.sequence, POTMsgSet.id
            FROM POTMsgSet
            LEFT JOIN TranslationTemplateItem AS ExistingEntry ON
                ExistingEntry.potmsgset = potmsgset.id
            WHERE
                POTMsgSet.id >= %s AND
                POTMsgSet.id < %s AND
                POTMsgSet.sequence > 0 AND
                ExistingEntry.id IS NULL
            """ % sqlvalues(self.last_id, end_id))
        self.logger.info("Inserted %d rows." % cur.rowcount)
        self.txn.commit()
        self.txn.begin()
        self.last_id = end_id


class PopulateMessageSharingSchema(LaunchpadScript):
    description = (
        "Populate columns and linking table added for Translations Message "
        "sharing.")

    def main(self):
        self.logger.info("Populating new TranslationMessage columns.")
        tm_loop = PopulateTranslationMessage(self.txn, self.logger)
        DBLoopTuner(tm_loop, 2).run()

        self.logger.info("Populating TranslationTemplateItem.")
        tti_loop = PopulateTranslationTemplateItem(self.txn, self.logger)
        DBLoopTuner(tti_loop, 2).run()


if __name__ == '__main__':
    script = PopulateMessageSharingSchema(
        'canonical.launchpad.scripts.message-sharing-populate')
    script.run()


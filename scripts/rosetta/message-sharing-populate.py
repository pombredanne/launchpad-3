#! /usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

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

from canonical.config import config
from canonical.database.sqlbase import cursor, quote
from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.scripts.base import LaunchpadScript
from canonical.launchpad.utilities.looptuner import LoopTuner


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

        cur.execute("SELECT max(id) FROM temp_todo")
        highest_id, = cur.fetchall()
        self.finish_id = highest_id = 1

    def isDone(self):
        """See `ITunableLoop`."""
        return self.last_id < self.finish_id

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
        end_id, = cur.fetchall()

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
            """ % quote(int(chunk_size)))
        self.logger.info(
            "Updated %d rows: %d - %d." % (chunk_size, self.last_id, end_id))
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

    def isDone(self):
        """See `ITunableLoop`."""
        return self.done

    def __call__(self, chunk_size):
        """See `ITunableLoop`."""
        chunk_size = int(chunk_size)
        cur = cursor()
        cur.execute("""
            INSERT INTO TranslationTemplateItem(
                potemplate, sequence, potmsgset)
            SELECT potemplate, sequence, id
            FROM POTMsgSet
            WHERE
                sequence > 0 AND
                POTMsgSet.id NOT IN (
                    SELECT potmsgset
                    FROM TranslationTemplateItem
                    )
            LIMIT %s
            """ % quote(int(chunk_size)))
        self.done = (cur.rowcount == 0)
        self.logger.info("Inserted %d rows." % chunk_size)
        self.txn.commit()
        self.txn.begin()


class PopulateMessageSharingSchema(LaunchpadScript):
    description = (
        "Populate columns and linking table added for Translations Message "
        "sharing.")

    def main(self):
        self.logger.info("Populating new TranslationMessage columns.")
        tm_loop = PopulateTranslationMessage(self.txn, self.logger)
        LoopTuner(tm_loop, 2).run()

        self.logger.info("Populating TranslationTemplateItem.")
        tti_loop = PopulateTranslationTemplateItem(self.txn, self.logger)
        LoopTuner(tti_loop, 2).run()


if __name__ == '__main__':
    script = PopulateMessageSharingSchema(
        'canonical.launchpad.scripts.message-sharing-populate')
    script.run()


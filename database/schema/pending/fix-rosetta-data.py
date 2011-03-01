#!/usr/bin/python
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Substitute some chars with the right value in POTranslation.translation."""

__metaclass__ = type
__all__ = []

from optparse import OptionParser
import sys

from canonical.lp import initZopeless
from canonical.database.sqlbase import cursor, sqlvalues
from canonical.launchpad.scripts import logger_options, logger

mapping = {
    # u'\u2022': u' ',  # space represented as a dot.
    u'\u21b5': u'\n', # new line represented with a graphical char.
    }

def change_char(ztm, log, character, newchar):
    """Substitute character with newchar in POTranslation.translation."""
    log.info("Changing all ocurrences of %r with %r" % (character, newchar))
    cur = cursor()
    cur.execute("""
        SELECT POTranslation.id, POTranslation.translation
        FROM POTranslation
        WHERE translation like %s
        """ % sqlvalues('%%%s%%' % character.encode('UTF-8')))

    log.info("Found %d translations that may need a fix" % cur.rowcount)

    for potranslation_id, translation in list(cur.fetchall()):
        cur = cursor()

        # Get the list of POMsgSet that will be affected by this change.
        cur.execute("""
            SELECT DISTINCT POSubmission.pomsgset
            FROM POSubmission
              JOIN POMsgSet ON POSubmission.pomsgset = POMsgSet.id
              JOIN POTMsgSet ON POMsgSet.potmsgset = POTMsgSet.id
              JOIN POMsgID ON POTMsgSet.primemsgid = POMsgID.id
            WHERE
              POSubmission.potranslation = %s AND
              POSubmission.active IS TRUE AND
              POMsgID.msgid NOT like %s
            """ % sqlvalues(
                potranslation_id, '%%%s%%' % character.encode('UTF-8')))

        log.info("Changing %d submissions for IPOTranslation %d" % (
            cur.rowcount, potranslation_id))

        pomsgset_ids = [str(id) for [id] in cur.fetchall()]
        if len(pomsgset_ids) > 0:
            # There is someone using this translation, update its review date
            # so new file exports will get this change.
            cur.execute("""
                UPDATE POMsgSet
                SET date_reviewed = (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
                WHERE id IN (%s)
                """ % ','.join(pomsgset_ids))
            log.info("Updated %d submissions for IPOTranslation %d" % (
                cur.rowcount, potranslation_id))

            fixed_translation = translation.replace(
                character, newchar).encode('UTF-8')

            cur.execute("""
                SELECT id
                FROM POTranslation
                WHERE sha1(translation) = sha1(%s)
                """ % sqlvalues(fixed_translation))

            if cur.rowcount == 0:
                # The fixed translation is not yet in our database, let's add
                # it.
                cur.execute(
                    "INSERT INTO POTranslation(translation) VALUES(%s)" % (
                        sqlvalues(fixed_translation)))

                cur.execute("""
                    SELECT id
                    FROM POTranslation
                    WHERE translation = %s
                    """ % sqlvalues(fixed_translation))

            # Get the id of the fixed POTranslation.
            [existing_translation_id] = cur.fetchone()

            # Get the submissions that should point to the fixed translation.
            cur.execute("""
                SELECT id
                FROM POSubmission
                WHERE
                  potranslation = %d AND
                  pomsgset IN (%s) AND
                  active IS TRUE
                """ % (potranslation_id, ','.join(pomsgset_ids)))

            submission_ids = [str(id) for [id] in cur.fetchall()]

            # Link to the new fixed translation.
            cur.execute("""
                UPDATE POSubmission
                SET potranslation = %d
                WHERE id IN (%s)
                """ % (existing_translation_id, ','.join(submission_ids)))

            # Commit is done per IPOTranslation.
            ztm.commit()

def read_options():
    """Read the command-line options and return an options object."""
    parser = OptionParser()
    logger_options(parser)

    (options, args) = parser.parse_args()

    return options

def main():
    options = read_options()
    log = logger(options)

    ztm = None
    try:
        log.debug("Connecting to database")
        ztm = initZopeless()
        for oldchar, newchar in mapping.iteritems():
            change_char(ztm, log, oldchar, newchar)
        return 0
    except:
        log.exception("Unhandled exception")
        log.debug("Rolling back")
        if ztm is not None:
            ztm.abort()
        return 1

if __name__ == '__main__':
    sys.exit(main())

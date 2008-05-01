#!/usr/bin/env python
# Copyright 2006 Canonical Ltd. All rights reserved.

import sys
from optparse import OptionParser

from canonical.config import config
from canonical.lp import initZopeless
from canonical.database.sqlbase import cursor
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.database import POFile

POMSGSETID = 0
POSELECTIONID = 1
ACTIVESUBMISSION = 2
PUBLISHEDSUBMISSION = 3
PLURALFORM = 4
POSUBMISSIONID = 5
POTRANSLATION = 6
LATESTSUBMISSION = 7

def parse_options(args):
    """Parse a set of command line options.

    Return an optparse.Values object.
    """
    parser = OptionParser()

    parser.add_option("-c", "--check", dest="check",
        default=False,
        action='store_true',
        help=("Whether the script should only check if there are duplicated"
            "entries.")
        )

    # Add the verbose/quiet options.
    logger_options(parser)

    (options, args) = parser.parse_args(args)

    return options

def main(argv):
    options = parse_options(argv[1:])

    # Get the global logger for this task.
    logger_object = logger(options, 'rosetta-poimport')

    if options.check:
        logger_object.info('Starting the checking process.')
    else:
        logger_object.info('Starting the fixing process.')

    # Setup zcml machinery to be able to use getUtility
    execute_zcml_for_scripts()
    ztm = initZopeless(dbuser=config.rosettaadmin.dbuser)

    # Get the list of POFiles.
    cur = cursor()
    cur.execute("SELECT id FROM POFile")
    pofile_ids = cur.fetchall()
    pofile_ids = [set_entry[0] for set_entry in pofile_ids]

    duplicates_found = 0
    processed = 0
    for pofileid in pofile_ids:
        # Get all its POMsgSet entries.
        cur = cursor()
        cur.execute("""
            SELECT
                POMsgSet.id,
                POSelection.id,
                POSelection.activesubmission,
                POSelection.publishedsubmission,
                POSelection.pluralform,
                POSubmission.id,
                POSubmission.potranslation,
                POFile.latestsubmission
            FROM
                POFile
                JOIN POMsgSet ON POMsgSet.pofile = POFile.id
                JOIN POSubmission ON POSubmission.pomsgset = POMsgSet.id
                LEFT OUTER JOIN POSelection ON
                    POSelection.pomsgset = POMsgSet.id AND
                    POSelection.pluralform = POSubmission.pluralform
            WHERE POFile.id = %d
            ORDER BY
                POMsgSet.id, POSubmission.pluralform,
                POSubmission.potranslation, POSubmission.datecreated;
            """ % pofileid)

        rows = cur.fetchall()
        current_pomsgset = None
        needs_recalculate = False
        duplicated_ids = []
        for row in rows:
            if current_pomsgset != row[POMSGSETID]:
                # It's a new POMsgSet
                current_pomsgset = row[POMSGSETID]
                current_pluralform = None
            if current_pluralform != row[PLURALFORM]:
                current_pluralform = row[PLURALFORM]
                current_translation = None
                current_posubmission = None
            if current_translation != row[POTRANSLATION]:
                current_translation = row[POTRANSLATION]
                current_posubmission = row[POSUBMISSIONID]
            else:
                # This submission is a duplicate of current_posubmission
                # because the translations are the same, and we should have
                # just one posubmission for a given translation.
                duplicated_ids.append(row[POSUBMISSIONID])
                duplicates_found += 1

                if options.check:
                    # We are only checking, don't execute the write
                    # operations.
                    continue

                if row[ACTIVESUBMISSION] == row[POSUBMISSIONID]:
                    # We need to remove this reference to the submission we
                    # are going to remove later because it's a duplicate.
                    cur = cursor()
                    cur.execute("""
                        UPDATE POSelection
                        SET activesubmission = %d
                        WHERE id = %d""" % (
                            current_posubmission, row[POSELECTIONID]))

                if row[PUBLISHEDSUBMISSION] == row[POSUBMISSIONID]:
                    # We need to remove this reference to the submission we
                    # are going to remove later because it's a duplicate.
                    cur = cursor()
                    cur.execute("""
                        UPDATE POSelection
                        SET publishedsubmission = %d
                        WHERE id = %d""" % (
                            current_posubmission, row[POSELECTIONID]))
                if row[LATESTSUBMISSION] == row[POSUBMISSIONID]:
                    # We need to remove this reference to the submission we
                    # are going to remove later because it's a duplicate.
                    cur = cursor()
                    cur.execute("""
                        UPDATE POFile
                        SET latestsubmission = NULL
                        WHERE id = %d""" % pofileid)
                    needs_recalculate = True
            processed += 1
            if processed % 50000 == 0:
                logger_object.info('Processed %d POSubmissions' % processed)

        if not options.check:
            for duplicate in duplicated_ids:
                # Remove all duplicates.
                cur = cursor()
                cur.execute(
                    "DELETE FROM POSubmission WHERE id = %d" % duplicate)
            if needs_recalculate:
                # We removed the latestsubmission for this
                # entry, we need to recalculate it now that the
                # duplicate entries are removed.
                pofile = POFile.get(pofileid)
                pofile.recalculateLatestSubmission()
            ztm.commit()

    if options.check:
        logger_object.info(
            'Finished the checking process and found %d entries to be fixed'
            ' in %d POSubmissions objects.' % (duplicates_found, processed))
    else:
        logger_object.info(
            'Finished the fixing process. We fixed %d duplicates in %d'
            ' POSubmissions objects.' % (duplicates_found, processed))


if __name__ == '__main__':
    main(sys.argv)

#!/usr/bin/env python
# Copyright 2006 Canonical Ltd. All rights reserved.

import sys
from optparse import OptionParser

from canonical.config import config
from canonical.lp import initZopeless
from canonical.database.sqlbase import cursor, sqlvalues
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.database import POMsgSet, POSubmission

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
    ztm = initZopeless(dbuser=config.rosetta.rosettaadmin.dbuser)

    # Get the list of IPOMsgSet in our system.
    cur = cursor()
    cur.execute("""
        SELECT id
        FROM POMsgSet
        """)
    pomsgset_ids = cur.fetchall()
    pomsgset_ids = [set_entry[0] for set_entry in pomsgset_ids]
    logger_object.info('There are %d msgsets to be checked' %
        len(pomsgset_ids))

    duplicates_found = 0
    processed = 0
    for id in pomsgset_ids:
        pomsgset = POMsgSet.get(id)
        pofile = pomsgset.pofile
        for pluralform in range(pomsgset.pluralforms):
            selection = pomsgset.getSelection(pluralform)
            submissions = POSubmission.select("""
                pomsgset = %s AND
                pluralform = %s""" % sqlvalues(pomsgset.id, pluralform),
                orderBy='datecreated')

            duplicated_ids = []
            duplicated_objects = []
            for submission in submissions:
                if submission.id in duplicated_ids:
                    continue
                duplicates = POSubmission.select("""
                    id <> %s AND
                    pomsgset = %s AND
                    pluralform = %s AND
                    potranslation = %s""" % sqlvalues(
                        submission.id, pomsgset.id, pluralform,
                        submission.potranslation))
                for duplicated in duplicates:
                    if not options.check:
                        if selection is not None:
                            if (selection.active is not None and
                                selection.active.id == duplicated.id):
                                selection.active = submission
                            if (selection.published is not None and
                                selection.published.id == duplicated.id):
                                selection.published = submission
                        if (pofile.latestsubmission is not None and
                            pofile.latestsubmission.id == duplicated.id):
                            pofile.latestsubmission = submission
                    duplicated_ids.append(duplicated.id)
                    duplicated_objects.append(duplicated)
                    duplicates_found += 1
            if not options.check:
                for duplicate in duplicated_objects:
                    duplicate.destroySelf()
        ztm.commit()
        processed += 1
        if processed % 50 == 0:
            logger_object.info('Processed %d POMsgSets' % processed)

    if options.check:
        logger_object.info(
            'Finished the checking process and found %d entries to be fixed' %
                duplicates_found)
    else:
        logger_object.info(
            'Finished the fixing process. We fixed %d duplicates' %
                duplicates_found)


if __name__ == '__main__':
    main(sys.argv)

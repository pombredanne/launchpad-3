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

    # We are going to process all POMsgSet in our database, and that's a lot
    # of rows. Just fetching the ids for those rows took more than 2.5GB of
    # memory so we need to get/process them in small chunks.
    start_chunk = 0
    chunk_size = 50000
    duplicates_found = 0
    processed = 0

    # Let's see the amount of entries we have in our database.
    cur = cursor()
    cur.execute("SELECT count(id) from POMsgSet")
    # It's only one row with a single field.
    amount_of_entries = cur.fetchall()[0][0]
    while True:
        # Get a new chunk of POMsgSet.id.
        cur = cursor()
        cur.execute("""
            SELECT id
            FROM POMsgSet
            WHERE id > %d AND id <= %d
            """ % (start_chunk, start_chunk + chunk_size))
        start_chunk += chunk_size
        pomsgset_ids = cur.fetchall()
        pomsgset_ids = [set_entry[0] for set_entry in pomsgset_ids]
        if len(pomsgset_ids) == 0 and start_chunk > amount_of_entries:
            # There aren't more ids, we can exit from the loop.
            # We use 'amount_of_entries' because we could have a 'hole' of
            # entries that would make us think that we don't have more entries
            # so we use the know amount of entries as an extra condition to
            # process all entries. We also check for len(pomsgset_ids) because
            # would happen that the number of entries increases while we are
            # doing this migration, so we are sure that we process any new
            # entry added after the initial count.
            break

        for id in pomsgset_ids:
            # Fetch the SQLObject for this id.
            pomsgset = POMsgSet.get(id)
            pofile = pomsgset.pofile
            for pluralform in range(pomsgset.pluralforms):
                selection = pomsgset.getSelection(pluralform)
                # We get all submissions for this concrete POMsgSet and
                # pluralform order by datecreated so we process firt the
                # older ones to remove the newer.
                submissions = POSubmission.select("""
                    pomsgset = %s AND
                    pluralform = %s""" % sqlvalues(pomsgset.id, pluralform),
                    orderBy='datecreated')

                duplicated_ids = []
                duplicated_objects = []
                for submission in submissions:
                    if submission.id in duplicated_ids:
                        # This submission has been detected as a duplicate, we
                        # don't need to find duplicates of this one.
                        continue
                    # Find all duplicates for this POSubmission.
                    duplicates = POSubmission.select("""
                        id <> %s AND
                        pomsgset = %s AND
                        pluralform = %s AND
                        potranslation = %s""" % sqlvalues(
                            submission.id, pomsgset.id, pluralform,
                            submission.potranslation))
                    for duplicated in duplicates:
                        if not options.check:
                            # We are not checking the database status, we need
                            # to start fixing the data.
                            if selection is not None:
                                if (selection.active is not None and
                                    selection.active.id == duplicated.id):
                                    # This duplicate entry is being used as
                                    # the active one. We want to remove it
                                    # from our system so we need to remove
                                    # that reference and thus we point to the
                                    # submission that will stay.
                                    selection.active = submission
                                if (selection.published is not None and
                                    selection.published.id == duplicated.id):
                                    # This duplicate entry is being used as
                                    # the published one. We want to remove it
                                    # from our system so we need to remove
                                    # that reference and thus we point to the
                                    # submission that will stay.
                                    selection.published = submission
                            if (pofile.latestsubmission is not None and
                                pofile.latestsubmission.id == duplicated.id):
                                # This duplicate entry is being used as
                                # the latestsubmission. We want to remove it
                                # from our system so we need to remove
                                # that reference.
                                pofile.latestsubmission = None
                        duplicated_ids.append(duplicated.id)
                        duplicated_objects.append(duplicated)
                        duplicates_found += 1
                if not options.check:
                    for duplicate in duplicated_objects:
                        # Remove all duplicates.
                        duplicate.destroySelf()
                    if pofile.latestsubmission is None:
                        # Seems like we removed the latestsubmission for this
                        # entry, we need to recalculate it now that the
                        # duplicate entries are removed.
                        pofile.recalculateLatestSubmission()
            ztm.commit()
            processed += 1
            if processed % 5000 == 0:
                logger_object.info('Processed %d POMsgSets' % processed)

    if options.check:
        logger_object.info(
            'Finished the checking process and found %d entries to be fixed'
            ' in %d POMsgSet objects.' % (duplicates_found, processed))
    else:
        logger_object.info(
            'Finished the fixing process. We fixed %d duplicates in %d'
            ' POMsgSet objects.' % (duplicates_found, processed))


if __name__ == '__main__':
    main(sys.argv)

#!/usr/bin/env python
# Copyright 2006 Canonical Ltd. All rights reserved.

import sys
from optparse import OptionParser
from zope.component import getUtility

from canonical.config import config
from canonical.lp import initZopeless
from canonical.database.sqlbase import cursor
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.database import POFile
from canonical.launchpad.interfaces import ILaunchpadCelebrities

def parse_options(args):
    """Parse a set of command line options.

    Return an optparse.Values object.
    """
    parser = OptionParser()

    parser.add_option("-c", "--check", dest="check",
        default=False,
        action='store_true',
        help=("Whether the script should only check if the po file ownership"
              " is correct.")
        )

    # Add the verbose/quiet options.
    logger_options(parser)

    (options, args) = parser.parse_args(args)

    return options

def main(argv):
    options = parse_options(argv[1:])

    # Get the global logger for this task.
    logger_object = logger(options, 'rosetta-fixes')

    if options.check:
        logger_object.info('Starting the po file checking...')
    else:
        logger_object.info('Starting the po file process...')

    # Setup zcml machinery to be able to use getUtility
    execute_zcml_for_scripts()
    ztm = initZopeless(dbuser=config.poimport.dbuser)

    rosetta_expert = getUtility(ILaunchpadCelebrities).rosetta_expert
    cur = cursor()
    cur.execute("SELECT id FROM POFile")
    pofile_ids = cur.fetchall()
    pofile_ids = [set_entry[0] for set_entry in pofile_ids]
    fixed_entries = 0
    for pofile_id in pofile_ids:
        pofile = POFile.get(pofile_id)
        # Store current owner as a backup.
        current_owner = pofile.owner
        # We need to change the owner to someone that always have permissions,
        # like Rosetta experts, to be sure that the old owner has permissions
        # already to edit that file, this is needed because IPOFile.owner has
        # always permissions and we want to ignore that check to be sure
        # whether it needs to be fixed.
        pofile.owner = rosetta_expert
        if pofile.canEditTranslations(current_owner):
            # The original owner has enough permissions to keep the ownership
            # of this file.
            pofile.owner = current_owner
        else:
            fixed_entries += 1

        if options.check:
            ztm.abort()
        else:
            ztm.commit()

    if options.check:
        if fixed_entries > 0:
            logger_object.info('There are %d of %d po files to fix.' %
                (fixed_entries, len(pofile_ids)))
        else:
            logger_object.info('All po files ownership are correct.')
    else:
        logger_object.info(
            'Fixed %d of %d' % (fixed_entries, len(pofile_ids)))

    logger_object.info('Finished.')


if __name__ == '__main__':
    main(sys.argv)

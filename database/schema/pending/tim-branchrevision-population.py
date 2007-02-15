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

def get_ancestry(revision, rev_map, cloud):
    "return the revision ids for the ancestry"
    ancestry = set([rev_map[revision]])

    for parent in cloud.get(revision, []):
        ancestry = ancestry.union(get_ancestry(parent, rev_map, cloud))

    return ancestry

def main(argv):
    options = parse_options(argv[1:])

    # Get the global logger for this task.
    logger_object = logger(options, 'branchrevision-population')

    if options.check:
        logger_object.info('Starting the checking process.')
    else:
        logger_object.info('Starting the fixing process.')

    # Setup zcml machinery to be able to use getUtility
    execute_zcml_for_scripts()
    ztm = initZopeless(dbuser=config.branchscanner.dbuser)

    # build a revision cloud
    cur = cursor()
    cur.execute("""
        SELECT Revision.id, Revision.revision_id, RevisionParent.parent_id
        FROM Revision
        LEFT OUTER JOIN RevisionParent ON
            RevisionParent.revision = Revision.id
        ORDER BY Revision.id, RevisionParent.sequence
        """)
    rev_map = {}
    cloud = {}
    for id, rev_id, parent_rev_id in cur.fetchall():
        rev_map[rev_id] = id
        if parent_rev_id is not None:
            cloud.setdefault(rev_id, []).append(parent_rev_id)

    # load all the branch revisions
    cur.execute("""
        SELECT branch, revision, sequence
        FROM BranchRevision
        ORDER BY branch, sequence
        """)

    branch_history = {}
    branch_ancestry = {}
    for branch, revision, sequence in cur.fetchall():
        if sequence is not None:
            branch_history.setdefault(branch, []).append(revision)
        branch_ancestry.setdefault(branch, set()).add(revision)

    id2rev = dict([(value, key) for key, value in rev_map.iteritems()])

    logger_object.debug('Branch histories:')
    for branch, history in branch_history.iteritems():
        db_ancestry = branch_ancestry[branch]
        logger_object.debug('\t%s:\t%s', branch, history)
        logger_object.debug('\t\t%s', db_ancestry)
        ancestry = get_ancestry(id2rev[history[-1]], rev_map, cloud)
        logger_object.debug('\t\t%s', ancestry)
        for rev_id in ancestry:
            if rev_id not in db_ancestry:
                if options.check:
                    logger_object.info(
                        'Revision id %s needs to be added to'
                        ' BranchRevision for branch %s' % (
                        rev_id, branch))
                else:
                    # do it
                    cur.execute("""
                    INSERT INTO BranchRevision
                    (branch, revision)
                    values (%s, %s)
                    """ % (branch, rev_id))
                    logger_object.info(
                        'Added Revision id %s to ancestry for branch %s' % (
                        rev_id, branch))
        

    if not options.check:
        ztm.commit()

if __name__ == '__main__':
    main(sys.argv)

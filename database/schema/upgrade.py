#!/usr/bin/python2.4
# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403
"""
Apply all outstanding schema patches to an existing launchpad database

TODO: Currently this gives no feedback on how violent the modifications
of a patch are (eg. how many rows updated). If we split the patches into
statements we could split out some statistics for manual eyeballing.
-- StuartBishop 20050602
"""

__metaclass__ = type

import _pythonpath # Sort PYTHONPATH

import os.path, glob, re, sys
from optparse import OptionParser

from canonical.launchpad.scripts import db_options, logger_options, logger
from canonical.database.sqlbase import connect

def main():
    schema_dir = os.path.dirname(__file__)

    con = connect(options.dbuser)

    # trusted.sql contains all our stored procedures, which may be required
    # for patches to apply correctly so must be run first.
    apply_other(con, 'trusted.sql')

    dbpatches = applied_patches(con)

    # Generate a list of all patches we might want to apply
    patches = []
    all_patch_files = glob.glob(
            os.path.join(schema_dir, 'patch-???-??-?.sql'))
    all_patch_files.sort()
    for patch_file in all_patch_files:
        m = re.search('patch-(\d\d\d)-(\d\d)-(\d).sql$', patch_file)
        if m is None:
            log.fatal('Invalid patch filename %s' % repr(patch_file))
            sys.exit(1)

        major, minor, patch = [int(i) for i in m.groups()]
        if (major, minor, patch) in dbpatches:
            continue # This patch has already been applied
        log.debug("Found patch %d.%d.%d -- %s" % (
            major, minor, patch, patch_file
            ))
        patches.append(((major, minor, patch), patch_file))

    # Apply the patches
    for (major, minor, patch), patch_file in patches:
        apply_patch(con, major, minor, patch, patch_file)

    # Update comments.
    apply_other(con, 'comments.sql')

    # Commit changes
    if options.commit:
        log.debug("Committing changes")
        con.commit()


def applied_patches(con):
    """Return a list of all patches that have been applied to the database.
    """
    cur = con.cursor()
    cur.execute("SELECT major, minor, patch FROM LaunchpadDatabaseRevision")
    return [tuple(row) for row in cur.fetchall()]


def apply_patch(con, major, minor, patch, patch_file):
    log.info("Applying %s" % patch_file)
    cur = con.cursor()
    full_sql = open(patch_file).read()

    # Strip comments
    full_sql = re.sub('(?xms) \/\* .*? \*\/', '', full_sql)
    full_sql = re.sub('(?xm) ^\s*-- .*? $', '', full_sql)

    statement_re = re.compile(
            r"( (?: [^; \$] | \$ (?! \$) | \$\$.*? \$\$ | \s)+ )",
            re.DOTALL | re.MULTILINE | re.VERBOSE
            )
    for sql in statement_re.split(full_sql):
        sql = sql.strip()
        if sql and sql != ';':
            cur.execute(sql) # Will die on a bad patch.

    # Ensure the patch updated LaunchpadDatabaseRevision. We could do this
    # automatically and avoid the boilerplate, but then we would lose the
    # ability to easily apply the patches manually.
    if (major, minor, patch) not in applied_patches(con):
        log.fatal("%s failed to update LaunchpadDatabaseRevision correctly"
                % patch_file)
        sys.exit(2)

    # Commit changes if we allow partial updates.
    if options.commit and options.partial:
        log.debug("Committing changes")
        con.commit()


def apply_other(con, script):
    log.info("Applying %s" % script)
    cur = con.cursor()
    path = os.path.join(os.path.dirname(__file__), script)
    sql = open(path).read()
    cur.execute(sql)

    if options.commit and options.partial:
        log.debug("Committing changes")
        con.commit()


if __name__ == '__main__':
    parser = OptionParser()
    db_options(parser)
    logger_options(parser)
    parser.add_option(
            "-n", "--dry-run", dest="commit", default=True,
            action="store_false", help="Don't actually commit changes"
            )
    parser.add_option(
            "-p", "--partial", dest="partial", default=False,
            action="store_true",
            help="Commit after applying each patch",
            )
    (options, args) = parser.parse_args()

    if args:
        parser.error("Too many arguments")

    log = logger(options)
    main()


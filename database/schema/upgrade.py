#!/usr/bin/python2.4
# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403
"""
Apply all outstanding schema patches to an existing launchpad database
"""

__metaclass__ = type

import _pythonpath # Sort PYTHONPATH

from cStringIO import StringIO
import glob
import os.path
from optparse import OptionParser
import re
import subprocess
import sys
from tempfile import NamedTemporaryFile
from textwrap import dedent
import time

from canonical.launchpad.scripts import db_options, logger_options, logger
from canonical.database.sqlbase import connect, ISOLATION_LEVEL_AUTOCOMMIT
import replication.helpers


SCHEMA_DIR = os.path.dirname(__file__)


def main():
    con = connect(options.dbuser)
    if replication.helpers.slony_installed(con):
        con.close()
        log.info("Applying patches to Slony-I environment.")
        apply_patches_replicated()
    else:
        log.info("Applying patches to unreplicated environment.")
        apply_patches_normal(con)

    return 0


def apply_patches_normal(con):
    """Update a non replicated database."""
    # trusted.sql contains all our stored procedures, which may
    # be required for patches to apply correctly so must be run first.
    apply_other(con, 'trusted.sql')

    # Apply the patches
    patches = get_patchlist(con)
    for (major, minor, patch), patch_file in patches:
        apply_patch(con, major, minor, patch, patch_file)

    # Update comments.
    apply_comments(con)

    # Commit changes
    if options.commit:
        log.debug("Committing changes")
        con.commit()


def apply_patches_replicated():
    """Update a Slony-I cluster."""

    # Get an autocommit connection. We use autocommit so we don't have to
    # worry about blocking locks needed by Slony-I.
    con = connect(options.dbuser, isolation=ISOLATION_LEVEL_AUTOCOMMIT)

    # Put our connection into autocommit mode so it doesn't conflict
    # with the locks Slony-I will need to make.
    con.rollback()
    con.set_isolation_level(0)

    # We use three slonik scripts to apply our DB patches.
    # The first script applies the DB patches to all nodes.

    # First make sure the cluster is synced.
    log.info("Waiting for cluster to sync.")
    replication.helpers.sync(timeout=600)

    outf = StringIO()
    
    # Start a transaction block.
    print >> outf, "try {"

    def run_sql(script):
        if os.path.isabs(script):
            full_path = script
        else:
            full_path = os.path.abspath(os.path.join(SCHEMA_DIR, script))
        assert os.path.exists(full_path), "%s doesn't exist." % full_path
        print >> outf, dedent("""\
            execute script (
                set id = @lpmain_set_id, event node = @master_id,
                filename='%s'
                );
            """ % full_path)

    # Apply trusted.sql
    run_sql('trusted.sql')

    # We are going to generate some temporary files using
    # NamedTempoararyFile. Store them here so we can control when
    # they get closed and cleaned up.
    temporary_files = []

    # Apply DB patches.
    patches = get_patchlist(con)
    for (major, minor, patch), patch_file in patches:
        run_sql(patch_file)
        # Cause a failure if the patch neglected to update
        # LaunchpadDatabaseRevision.
        assert_script = NamedTemporaryFile(prefix='assert', suffix='.sql')
        print >> assert_script, dedent("""
            SELECT assert_patch_applied(%d, %d, %d);
            """ % (major, minor, patch))
        assert_script.flush()
        run_sql(assert_script.name)
        temporary_files.append(assert_script)

    # Apply comments.sql. Default slonik refuses to run it as one
    # 'execute script' because it contains too many statements, so chunk
    # it (we don't want to rebuild slony with a higher limit).
    comments = re.findall(
            "(?ms).*?'\s*;\s*$", open('comments.sql', 'r').read())
    while comments:
        comment_file = NamedTemporaryFile(prefix="comments", suffix=".sql")
        print >> comment_file, '\n'.join(comments[:1000])
        del comments[:1000]
        comment_file.flush()
        run_sql(comment_file.name)
        # Store a reference so it doesn't get garbage collected before our
        # slonik script is run.
        temporary_files.append(comment_file)

    # Close transaction block and abort on error.
    print >> outf, dedent("""\
            }
            on error {
                echo 'Failed! Slonik script aborting. Patches rolled back.';
                exit 1;
                }
            """)

    # Execute the script with slonik.
    if not replication.helpers.execute_slonik(outf.getvalue()):
        log.fatal("Aborting.")

    # Cleanup our temporary files - they applied successfully.
    for temporary_file in temporary_files:
        temporary_file.close()
    del temporary_files

    # Wait for replication to sync.
    replication.helpers.sync(timeout=0)

    # The db patches have now been applied to all nodes, and we are now
    # committed to completing the upgrade (!). If any of the later stages
    # fail, it will likely involve manual cleanup.

    # We now scan for new tables and add them tables and them to their
    # desired replication sets using a second script.

    # Detect new tables and sequences and their replication sets.

    # Create a new replication set to hold new tables and sequences

    # Add the new tables and sequences to the holding set.

    # Subscribe the holding set to the replica.

    # Sync.

    # Merge the holding set into the target set.

    # Sync.

    # We also scan for tables we want to drop and do so using
    # a final slonik script.


    # Detect tables we want to drop. Remove them from their replication
    # sets and drop.


def get_patchlist(con):
    """Return a patches that need to be applied to the connected database
    in [((major, minor, patch), patch_file)] format.
    """
    dbpatches = applied_patches(con)

    # Generate a list of all patches we might want to apply
    patches = []
    all_patch_files = glob.glob(
            os.path.join(SCHEMA_DIR, 'patch-???-??-?.sql'))
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
    return patches


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

    # Regular expression to extract a single statement.
    # A statement may contain semicolons if it is a stored procedure
    # definition, which requires a disgusting regexp or a parser for
    # PostgreSQL specific SQL.
    statement_re = re.compile(
            r"( (?: [^;$] | \$ (?! \$) | \$\$.*? \$\$)+ )",
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
    if options.slonik:
        slonik_execute_script(options.slonik, script)
    else:
        cur = con.cursor()
        path = os.path.join(os.path.dirname(__file__), script)
        sql = open(path).read()
        cur.execute(sql)

        if options.commit and options.partial:
            log.debug("Committing changes")
            con.commit()


def apply_comments(con):
    apply_other(con, 'comments.sql')


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

    if options.commit is False and options.slonik:
        parser.error("--dry-run does not make sense with --slonik")

    log = logger(options)
    main()

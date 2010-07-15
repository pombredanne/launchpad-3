#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Apply all outstanding schema patches to an existing launchpad database
"""

__metaclass__ = type

# pylint: disable-msg=W0403
import _pythonpath # Sort PYTHONPATH

from cStringIO import StringIO
import glob
import os.path
from optparse import OptionParser
import re
import sys
from tempfile import NamedTemporaryFile
from textwrap import dedent

from canonical.launchpad.scripts import db_options, logger_options, logger
from canonical.database.sqlbase import connect, ISOLATION_LEVEL_AUTOCOMMIT
from canonical.database.postgresql import fqn
import replication.helpers


SCHEMA_DIR = os.path.dirname(__file__)


def main():
    con = connect(options.dbuser)
    if replication.helpers.slony_installed(con):
        con.close()
        if options.commit is False:
            parser.error("--dry-run does not make sense with replicated db")
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
                set id = @lpmain_set, event node = @master_node,
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
    comments_path = os.path.join(os.path.dirname(__file__), 'comments.sql')
    comments = re.findall(
            "(?ms).*?'\s*;\s*$", open(comments_path, 'r').read())
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

    # We now scan for new tables and add them to the lpmain
    # replication set using a second script. Note that upgrade.py only
    # deals with the lpmain replication set.

    # Detect new tables and sequences.
    # Everything else that isn't replicated should go in the lpmain
    # replication set.
    cur = con.cursor()
    unrepl_tabs, unrepl_seqs = replication.helpers.discover_unreplicated(cur)

    # But warn if we are going to replicate something not in the calculated
    # set, as *_SEED in replication.helpers needs to be updated. We don't want
    # abort unless absolutely necessary to avoid manual cleanup.
    lpmain_tabs, lpmain_seqs = replication.helpers.calculate_replication_set(
            cur, replication.helpers.LPMAIN_SEED)

    assumed_tabs = unrepl_tabs.difference(lpmain_tabs)
    assumed_seqs = unrepl_seqs.difference(lpmain_seqs)
    for obj in (assumed_tabs.union(assumed_seqs)):
        log.warn(
            "%s not in calculated lpmain replication set. "
            "Update *_SEED in replication/helpers.py" % obj)

    if unrepl_tabs or unrepl_seqs:
        # TODO: Or if the holding set already exists - catch an aborted run.
        log.info(
            "New stuff needs replicating: %s"
            % ', '.join(sorted(unrepl_tabs.union(unrepl_seqs))))
        # Create a new replication set to hold new tables and sequences
        # TODO: Only create set if it doesn't already exist.
        outf = StringIO()
        print >> outf, dedent("""\
            try {
                create set (
                    id = @holding_set, origin = @master_node,
                    comment = 'Temporary set to merge'
                    );
            """)

        # Add the new tables and sequences to the holding set.
        cur.execute("""
            SELECT max(tab_id) FROM %s
            """ % fqn(replication.helpers.CLUSTER_NAMESPACE, 'sl_table'))
        next_id = cur.fetchone()[0] + 1
        for tab in unrepl_tabs:
            print >> outf, dedent("""\
                echo 'Adding %s to holding set for lpmain merge.';
                set add table (
                    set id = @holding_set, origin = @master_node, id=%d,
                    fully qualified name = '%s',
                    comment = '%s'
                    );
                """ % (tab, next_id, tab, tab))
            next_id += 1
        cur.execute("""
            SELECT max(seq_id) FROM %s
            """ % fqn(replication.helpers.CLUSTER_NAMESPACE, 'sl_sequence'))
        next_id = cur.fetchone()[0] + 1
        for seq in  unrepl_seqs:
            print >> outf, dedent("""\
                echo 'Adding %s to holding set for lpmain merge.';
                set add sequence (
                    set id = @holding_set, origin = @master_node, id=%d,
                    fully qualified name = '%s',
                    comment = '%s'
                    );
                """ % (seq, next_id, seq, seq))
            next_id += 1

        print >> outf, dedent("""\
            } on error {
                echo 'Failed to create holding set! Aborting.';
                exit 1;
                }
            """)

        # Subscribe the holding set to all replicas.
        # TODO: Only subscribe the set if not already subscribed.
        # Close the transaction and sync. Important, or MERGE SET will fail!
        # Merge the sets.
        # Sync.
        # Drop the holding set.
        for slave_node in replication.helpers.get_slave_nodes(con):
            print >> outf, dedent("""\
                echo 'Subscribing holding set to @node%d_node.';
                subscribe set (
                    id=@holding_set,
                    provider=@master_node, receiver=@node%d_node, forward=yes);
                echo 'Waiting for sync';
                sync (id=@master_node);
                wait for event (
                    origin=@master_node, confirmed=ALL,
                    wait on=@master_node, timeout=0
                    );
                """ % (slave_node.node_id, slave_node.node_id))

        print >> outf, dedent("""\
            echo 'Merging holding set to lpmain';
            merge set (
                id=@lpmain_set, add id=@holding_set, origin=@master_node
                );
            """)

        # Execute the script and sync.
        if not replication.helpers.execute_slonik(outf.getvalue()):
            log.fatal("Aborting.")
        replication.helpers.sync(timeout=0)

    # We also scan for tables and sequences we want to drop and do so using
    # a final slonik script. Instead of dropping tables in the DB patch,
    # we rename them into the ToDrop namespace.
    cur.execute("""
        SELECT nspname, relname, tab_id
        FROM pg_class
        JOIN pg_namespace ON relnamespace = pg_namespace.oid
        LEFT OUTER JOIN %s ON pg_class.oid = tab_reloid
        WHERE nspname='todrop' AND relkind='r'
        """ % fqn(replication.helpers.CLUSTER_NAMESPACE, 'sl_table'))
    tabs_to_drop = set(
        (fqn(nspname, relname), tab_id)
        for nspname, relname, tab_id in cur.fetchall())

    # Generate a slonik script to remove tables from the replication set,
    # and a DROP TABLE/DROP SEQUENCE sql script to run after.
    if tabs_to_drop:
        log.info("Dropping tables: %s" % ', '.join(
            name for name, id in tabs_to_drop))
        sk = StringIO()
        sql = NamedTemporaryFile(prefix="drop", suffix=".sql")
        print >> sk, "try {"
        for tab_name, tab_id in tabs_to_drop:
            if tab_id is not None:
                print >> sk, dedent("""\
                    echo 'Removing %s from replication';
                    set drop table (origin=@master_node, id=%d);
                    """ % (tab_name, tab_id))
            print >> sql, "DROP TABLE %s;" % tab_name
        sql.flush()
        print >> sk, dedent("""\
            execute script (
                set id=@lpmain_set, event node=@master_node,
                filename='%s'
                );
            }
            on error {
                echo 'Failed to drop tables. Aborting.';
                exit 1;
                }
            """ % sql.name)
        if not replication.helpers.execute_slonik(sk.getvalue()):
            log.fatal("Aborting.")
        sql.close()

    # Now drop sequences. We don't do this at the same time as the tables,
    # as most sequences will be dropped implicitly with the table drop.
    cur.execute("""
        SELECT nspname, relname, seq_id
        FROM pg_class
        JOIN pg_namespace ON relnamespace = pg_namespace.oid
        LEFT OUTER JOIN %s ON pg_class.oid = seq_reloid
        WHERE nspname='todrop' AND relkind='S'
        """ % fqn(replication.helpers.CLUSTER_NAMESPACE, 'sl_sequence'))
    seqs_to_drop = set(
        (fqn(nspname, relname), tab_id)
        for nspname, relname, tab_id in cur.fetchall())

    if seqs_to_drop:
        log.info("Dropping sequences: %s" % ', '.join(
            name for name, id in seqs_to_drop))
        # Generate a slonik script to remove sequences from the
        # replication set, DROP SEQUENCE sql script to run after.
        sk = StringIO()
        sql = NamedTemporaryFile(prefix="drop", suffix=".sql")
        print >> sk, "try {"
        for seq_name, seq_id in seqs_to_drop:
            if seq_id is not None:
                print >> sk, dedent("""\
                    echo 'Removing %s from replication';
                    set drop sequence (origin=@master_node, id=%d);
                    """ % (seq_name, seq_id))
            print >> sql, "DROP SEQUENCE %s;" % seq_name
        sql.flush()
        print >> sk, dedent("""\
            execute script (
                set id=@lpmain_set, event node=@master_node,
                filename='%s'
                );
            }
            on error {
                echo 'Failed to drop sequences. Aborting.';
                exit 1;
                }
            """ % sql.name)
        if not replication.helpers.execute_slonik(sk.getvalue()):
            log.fatal("Aborting.")
    replication.helpers.sync(timeout=0)


def get_patchlist(con):
    """Return a patches that need to be applied to the connected database
    in [((major, minor, patch), patch_file)] format.
    """
    dbpatches = applied_patches(con)

    # Generate a list of all patches we might want to apply
    patches = []
    all_patch_files = glob.glob(
        os.path.join(SCHEMA_DIR, 'patch-????-??-?.sql'))
    all_patch_files.sort()
    for patch_file in all_patch_files:
        m = re.search('patch-(\d+)-(\d+)-(\d).sql$', patch_file)
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

    log = logger(options)
    main()

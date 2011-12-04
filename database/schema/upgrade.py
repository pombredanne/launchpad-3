#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Apply all outstanding schema patches to an existing launchpad database
"""

__metaclass__ = type

# pylint: disable-msg=W0403
import _pythonpath  # Sort PYTHONPATH

from cStringIO import StringIO
import glob
import os.path
from optparse import OptionParser
import re
from tempfile import NamedTemporaryFile
from textwrap import dedent

from canonical.launchpad.scripts import db_options, logger_options, logger
from canonical.database.sqlbase import connect, ISOLATION_LEVEL_AUTOCOMMIT
from canonical.database.postgresql import fqn
import replication.helpers


SCHEMA_DIR = os.path.dirname(__file__)


def main():
    con = connect()
    patches = get_patchlist(con)

    if replication.helpers.slony_installed(con):
        con.close()
        if options.commit is False:
            parser.error("--dry-run does not make sense with replicated db")
        log.info("Applying patches to Slony-I environment.")
        apply_patches_replicated()
        con = connect()
    else:
        log.info("Applying patches to unreplicated environment.")
        apply_patches_normal(con)

    report_patch_times(con, patches)

    # Commit changes
    if options.commit:
        log.debug("Committing changes")
        con.commit()

    return 0


# When we apply a number of patches in a transaction, they all end up
# with the same start_time (the transaction start time). This SQL fixes
# that up by setting the patch start time to the previous patches end
# time when there are patches that share identical start times. The
# FIX_PATCH_TIMES_PRE_SQL stores the start time of patch application,
# which is probably not the same as the transaction timestamp because we
# have to apply trusted.sql before applying patches (in addition to
# other preamble time such as Slony-I grabbing locks).
# FIX_PATCH_TIMES_POST_SQL does the repair work.
FIX_PATCH_TIMES_PRE_SQL = dedent("""\
    CREATE TEMPORARY TABLE _start_time AS (
        SELECT statement_timestamp() AT TIME ZONE 'UTC' AS start_time);
    """)
FIX_PATCH_TIMES_POST_SQL = dedent("""\
    UPDATE LaunchpadDatabaseRevision
    SET start_time = prev_end_time
    FROM (
        SELECT
            LDR1.major, LDR1.minor, LDR1.patch,
            max(LDR2.end_time) AS prev_end_time
        FROM
            LaunchpadDatabaseRevision AS LDR1,
            LaunchpadDatabaseRevision AS LDR2
        WHERE
            (LDR1.major, LDR1.minor, LDR1.patch)
                > (LDR2.major, LDR2.minor, LDR2.patch)
            AND LDR1.start_time = LDR2.start_time
        GROUP BY LDR1.major, LDR1.minor, LDR1.patch
        ) AS PrevTime
    WHERE
        LaunchpadDatabaseRevision.major = PrevTime.major
        AND LaunchpadDatabaseRevision.minor = PrevTime.minor
        AND LaunchpadDatabaseRevision.patch = PrevTime.patch
        AND LaunchpadDatabaseRevision.start_time <> prev_end_time;

    UPDATE LaunchpadDatabaseRevision
    SET start_time=_start_time.start_time
    FROM _start_time
    WHERE
        LaunchpadDatabaseRevision.start_time
            = transaction_timestamp() AT TIME ZONE 'UTC';
    """)


def to_seconds(td):
    """Convert a timedelta to seconds."""
    return td.days * (24 * 60 * 60) + td.seconds + td.microseconds / 1000000.0


def report_patch_times(con, todays_patches):
    """Report how long it took to apply the given patches."""
    cur = con.cursor()

    todays_patches = [patch_tuple for patch_tuple, patch_file
        in todays_patches]

    cur.execute("""
        SELECT
            major, minor, patch, start_time, end_time - start_time AS db_time
        FROM LaunchpadDatabaseRevision
        WHERE start_time > CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
            - CAST('1 month' AS interval)
        ORDER BY major, minor, patch
        """)
    for major, minor, patch, start_time, db_time in cur.fetchall():
        if (major, minor, patch) in todays_patches:
            continue
        db_time = to_seconds(db_time)
        start_time = start_time.strftime('%Y-%m-%d')
        log.info(
            "%d-%02d-%d applied %s in %0.1f seconds"
            % (major, minor, patch, start_time, db_time))

    for major, minor, patch in todays_patches:
        cur.execute("""
            SELECT end_time - start_time AS db_time
            FROM LaunchpadDatabaseRevision
            WHERE major = %s AND minor = %s AND patch = %s
            """, (major, minor, patch))
        db_time = cur.fetchone()[0]
        # Patches before 2208-01-1 don't have timing information.
        # Ignore this. We can remove this code the next time we
        # create a new database baseline, as all patches will have
        # timing information.
        if db_time is None:
            log.debug('%d-%d-%d no application time', major, minor, patch)
            continue
        log.info(
            "%d-%02d-%d applied just now in %0.1f seconds",
            major, minor, patch, to_seconds(db_time))


def apply_patches_normal(con):
    """Update a non replicated database."""
    # trusted.sql contains all our stored procedures, which may
    # be required for patches to apply correctly so must be run first.
    apply_other(con, 'trusted.sql')

    # Prepare to repair patch timestamps if necessary.
    con.cursor().execute(FIX_PATCH_TIMES_PRE_SQL)

    # Apply the patches
    patches = get_patchlist(con)
    for (major, minor, patch), patch_file in patches:
        apply_patch(con, major, minor, patch, patch_file)

    # Repair patch timestamps if necessary.
    con.cursor().execute(FIX_PATCH_TIMES_POST_SQL)

    # Update comments.
    apply_comments(con)


def apply_patches_replicated():
    """Update a Slony-I cluster."""

    # Get an autocommit connection. We use autocommit so we don't have to
    # worry about blocking locks needed by Slony-I.
    con = connect(isolation=ISOLATION_LEVEL_AUTOCOMMIT)

    # We use three slonik scripts to apply our DB patches.
    # The first script applies the DB patches to all nodes.

    # First make sure the cluster is synced.
    log.info("Waiting for cluster to sync, pre-update.")
    replication.helpers.sync(timeout=600)

    outf = StringIO()

    # Start a transaction block.
    print >> outf, "try {"

    sql_to_run = []

    def run_sql(script):
        if os.path.isabs(script):
            full_path = script
        else:
            full_path = os.path.abspath(os.path.join(SCHEMA_DIR, script))
        assert os.path.exists(full_path), "%s doesn't exist." % full_path
        sql_to_run.append(full_path)

    # We are going to generate some temporary files using
    # NamedTempoararyFile. Store them here so we can control when
    # they get closed and cleaned up.
    temporary_files = []

    # Apply trusted.sql
    run_sql('trusted.sql')

    # We are going to generate some temporary files using
    # NamedTempoararyFile. Store them here so we can control when
    # they get closed and cleaned up.
    temporary_files = []

    # Apply DB patches as one big hunk.
    combined_script = NamedTemporaryFile(prefix='patch', suffix='.sql')
    temporary_files.append(combined_script)

    # Prepare to repair the start timestamps in
    # LaunchpadDatabaseRevision.
    print >> combined_script, FIX_PATCH_TIMES_PRE_SQL

    patches = get_patchlist(con)
    for (major, minor, patch), patch_file in patches:
        print >> combined_script, open(patch_file, 'r').read()

        # Trigger a failure if the patch neglected to update
        # LaunchpadDatabaseRevision.
        print >> combined_script, (
            "SELECT assert_patch_applied(%d, %d, %d);"
            % (major, minor, patch))

    # Fix the start timestamps in LaunchpadDatabaseRevision.
    print >> combined_script, FIX_PATCH_TIMES_POST_SQL

    combined_script.flush()
    run_sql(combined_script.name)

    # Now combine all the written SQL (probably trusted.sql and
    # patch*.sql) into one big file, which we execute with a single
    # slonik execute_script statement to avoid multiple syncs.
    single = NamedTemporaryFile(prefix='single', suffix='.sql')
    for path in sql_to_run:
        print >> single, open(path, 'r').read()
        print >> single, ""
    single.flush()

    print >> outf, dedent("""\
        execute script (
            set id = @lpmain_set, event node = @master_node,
            filename='%s'
            );
        """ % single.name)

    # Close transaction block and abort on error.
    print >> outf, dedent("""\
        }
        on error {
            echo 'Failed! Slonik script aborting. Patches rolled back.';
            exit 1;
            }
        """)

    # Execute the script with slonik.
    log.info("slonik(1) schema upgrade script generated. Invoking.")
    if not replication.helpers.execute_slonik(outf.getvalue()):
        log.fatal("Aborting.")
        raise SystemExit(4)
    log.info("slonik(1) schema upgrade script completed.")

    # Cleanup our temporary files - they applied successfully.
    for temporary_file in temporary_files:
        temporary_file.close()
    del temporary_files

    # Wait for replication to sync.
    log.info("Waiting for patches to apply to slaves and cluster to sync.")
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
                    id=@holding_set, provider=@master_node,
                    receiver=@node%d_node, forward=yes);
                wait for event (
                    origin=@master_node, confirmed=all,
                    wait on=@master_node, timeout=0);
                echo 'Waiting for sync';
                sync (id=@master_node);
                wait for event (
                    origin=@master_node, confirmed=ALL,
                    wait on=@master_node, timeout=0);
                """ % (slave_node.node_id, slave_node.node_id))

        print >> outf, dedent("""\
            echo 'Merging holding set to lpmain';
            merge set (
                id=@lpmain_set, add id=@holding_set, origin=@master_node);
            """)

        # Execute the script and sync.
        log.info(
            "Generated slonik(1) script to replicate new objects. Invoking.")
        if not replication.helpers.execute_slonik(outf.getvalue()):
            log.fatal("Aborting.")
        log.info(
            "slonik(1) script to replicate new objects completed.")
        log.info("Waiting for sync.")
        replication.helpers.sync(timeout=0)
    else:
        log.info("No new tables or sequences to replicate.")

    # We also scan for tables and sequences we want to drop and do so using
    # a final slonik script. Instead of dropping tables in the DB patch,
    # we rename them into the ToDrop namespace.
    #
    # First, remove all todrop.* sequences from replication.
    cur.execute("""
        SELECT seq_nspname, seq_relname, seq_id from %s
        WHERE seq_nspname='todrop'
        """ % fqn(replication.helpers.CLUSTER_NAMESPACE, 'sl_sequence'))
    seqs_to_unreplicate = set(
        (fqn(nspname, relname), tab_id)
        for nspname, relname, tab_id in cur.fetchall())
    if seqs_to_unreplicate:
        log.info("Unreplicating sequences: %s" % ', '.join(
            name for name, id in seqs_to_unreplicate))
        # Generate a slonik script to remove sequences from the
        # replication set.
        sk = StringIO()
        print >> sk, "try {"
        for seq_name, seq_id in seqs_to_unreplicate:
            if seq_id is not None:
                print >> sk, dedent("""\
                    echo 'Removing %s from replication';
                    set drop sequence (origin=@master_node, id=%d);
                    """ % (seq_name, seq_id))
        print >> sk, dedent("""\
            }
            on error {
                echo 'Failed to unreplicate sequences. Aborting.';
                exit 1;
                }
            """)
        log.info(
            "Generated slonik(1) script to unreplicate sequences. Invoking.")
        if not replication.helpers.execute_slonik(sk.getvalue()):
            log.fatal("Aborting.")
        log.info("slonik(1) script to drop sequences completed.")

    # Generate a slonik script to remove tables from the replication set,
    # and a DROP TABLE/DROP SEQUENCE sql script to run after.
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
        log.info("Generated slonik(1) script to drop tables. Invoking.")
        if not replication.helpers.execute_slonik(sk.getvalue()):
            log.fatal("Aborting.")
        log.info("slonik(1) script to drop tables completed.")
        sql.close()

    # Now drop any remaining sequences. Most sequences will be dropped
    # implicitly with the table drop.
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
        log.info("Generated slonik(1) script to drop sequences. Invoking.")
        if not replication.helpers.execute_slonik(sk.getvalue()):
            log.fatal("Aborting.")
        log.info("slonik(1) script to drop sequences completed.")
    log.info("Waiting for final sync.")
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
            raise SystemExit(1)

        major, minor, patch = [int(i) for i in m.groups()]
        if (major, minor, patch) in dbpatches:
            continue  # This patch has already been applied
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
    apply_other(con, patch_file, no_commit=True)

    # Ensure the patch updated LaunchpadDatabaseRevision. We could do this
    # automatically and avoid the boilerplate, but then we would lose the
    # ability to easily apply the patches manually.
    if (major, minor, patch) not in applied_patches(con):
        log.fatal("%s failed to update LaunchpadDatabaseRevision correctly"
                % patch_file)
        raise SystemExit(2)

    # Commit changes if we allow partial updates.
    if options.commit and options.partial:
        log.debug("Committing changes")
        con.commit()


def apply_other(con, script, no_commit=False):
    log.info("Applying %s" % script)
    cur = con.cursor()
    path = os.path.join(os.path.dirname(__file__), script)
    sql = open(path).read()
    if not sql.rstrip().endswith(';'):
        # This is important because patches are concatenated together
        # into a single script when we apply them to a replicated
        # environment.
        log.fatal(
            "Last non-whitespace character of %s must be a semicolon", script)
        raise SystemExit(3)
    cur.execute(sql)

    if not no_commit and options.commit and options.partial:
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
            "--partial", dest="partial", default=False,
            action="store_true",
            help="Commit after applying each patch",
            )
    (options, args) = parser.parse_args()

    if args:
        parser.error("Too many arguments")

    log = logger(options)
    main()

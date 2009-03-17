# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Common helpers for replication scripts."""

__metaclass__ = type
__all__ = []

import subprocess
import sys
from tempfile import NamedTemporaryFile
from textwrap import dedent

from canonical.config import config
from canonical.database.sqlbase import sqlvalues
from canonical.database.postgresql import (
    fqn, all_tables_in_schema, all_sequences_in_schema, ConnectionString
    )
from canonical.launchpad.scripts.logger import log


# The Slony-I clustername we use with Launchpad. Hardcoded because there
# is no point changing this, ever.
CLUSTERNAME = 'sl'

# The namespace in the database used to contain all the Slony-I tables.
CLUSTER_NAMESPACE = '_%s' % CLUSTERNAME


# Seed tables for the authdb replication set to be passed to
# calculate_replication_set().
AUTHDB_SEED = set([
    ])


# Seed tables for the lpmain replication set to be passed to
# calculate_replication_set().
LPMAIN_SEED = set([
    # These tables are scheduled to move to the authdb seed.
    ('public', 'account'),
    ('public', 'openidassociations'),
    ('public', 'oauthnonce'),

    ('public', 'person'),
    ('public', 'launchpaddatabaserevision'),
    ('public', 'fticache'),
    ('public', 'nameblacklist'),
    ('public', 'codeimportmachine'),
    ('public', 'scriptactivity'),
    ('public', 'standardshipitrequest'),
    ('public', 'bugtag'),
    ('public', 'launchpadstatistic'),
    ('public', 'parsedapachelog'),
    ('public', 'shipitsurvey'),
    ])


# Explicitly list tables that should not be replicated. This includes the
# session tables, as these might exist in developer databases but will not
# exist in the production launchpad database.
IGNORED_TABLES = set([
    'public.secret', 'public.sessiondata', 'public.sessionpkgdata'])


def slony_installed(con):
    """Return True if the connected database is part of a Launchpad Slony-I
    cluster.
    """
    cur = con.cursor()
    cur.execute("""
        SELECT TRUE FROM pg_class,pg_namespace
        WHERE
            nspname = %s
            AND relname = 'sl_table'
            AND pg_class.relnamespace = pg_namespace.oid
        """ % sqlvalues(CLUSTER_NAMESPACE))
    return cur.fetchone() is not None


class TableReplicationInfo:
    """Internal table replication details."""
    table_id = None
    replication_set_id = None
    master_node_id = None

    def __init__(self, con, namespace, table_name):
        cur = con.cursor()
        cur.execute("""
            SELECT tab_id, tab_set, set_origin
            FROM %s.sl_table, %s.sl_set
            WHERE tab_set = set_id
                AND tab_nspname = %s
                AND tab_relname = %s
            """ % (
                (CLUSTER_NAMESPACE, CLUSTER_NAMESPACE)
                + sqlvalues(namespace, table_name)))
        row = cur.fetchone()
        if row is None:
            raise LookupError(fqn(namespace, table_name))
        self.table_id, self.replication_set_id, self.master_node_id = row


def sync(timeout):
    """Generate a sync event and wait for it to complete on all nodes.
   
    This means that all pending events have propagated and are in sync
    to the point in time this method was called. This might take several
    hours if there is a large backlog of work to replicate.

    :param timeout: Number of seconds to wait for the sync. 0 to block
                    indefinitely.
    """
    return execute_slonik("", sync=timeout)


def execute_slonik(script, sync=None, exit_on_fail=True, auto_preamble=True):
    """Use the slonik command line tool to run a slonik script.

    :param script: The script as a string. Preamble should not be included.

    :param sync: Number of seconds to wait for sync before failing. 0 to
                 block indefinitely.

    :param exit_on_fail: If True, on failure of the slonik script
                         sys.exit is invoked using the slonik return code.

    :param auto_preamble: If True, the generated preamble will be
                          automatically included.

    :returns: True if the script completed successfully. False if
              exit_on_fail is False and the script failed for any reason.
    """

    # Add the preamble and optional sync to the script.
    if auto_preamble:
        script = preamble() + script

    if sync is not None:
        script = script + """
            sync (id = @master_node);
            wait for event (
                origin = ALL, confirmed = ALL,
                wait on = @master_node, timeout = %d);
            """ % sync

    # Copy the script to a NamedTemporaryFile rather than just pumping it
    # to slonik via stdin. This way it can be examined if slonik appears
    # to hang.
    script_on_disk = NamedTemporaryFile(prefix="slonik", suffix=".sk")
    print >> script_on_disk, script
    script_on_disk.flush()

    # Run slonik
    log.debug("Executing slonik script %s" % script_on_disk.name)
    #log.debug(script) # We need a log level < DEBUG :-(
    returncode = subprocess.call(['slonik', script_on_disk.name])

    if returncode != 0:
        log.error("slonik script failed")
        if exit_on_fail:
            sys.exit(1)

    return returncode == 0


def preamble():
    """Return the preable needed at the start of all slonik scripts."""

    master_connection_string = ConnectionString(config.database.main_master)
    slave_connection_string = ConnectionString(config.database.main_slave)
    master_connection_string.user = 'slony'
    slave_connection_string.user = 'slony'

    return dedent("""\
        # Every slonik script must start with a clustername, which cannot
        # be changed once the cluster is initialized.
        cluster name = sl;

        # Symbolic ids for nodes.
        define master_node 1;
        define slave1_node 2;

        # Symbolic ids for replication sets.
        define lpmain_set  1;
        define authdb_set  2;
        define holding_set 666;

        # Connection strings.
        define master_conninfo '%s';
        define slave1_conninfo '%s';

        # Connection strings so slonik knows where to go.
        node @master_node admin conninfo = @master_conninfo;
        node @slave1_node admin conninfo = @slave1_conninfo;
        """ % (master_connection_string, slave_connection_string))
        

def calculate_replication_set(cur, seeds):
    """Return the minimal set of tables and sequences needed in a
    replication set containing the seed table.

    A replication set must contain all tables linked by foreign key
    reference to the given table, and sequences used to generate keys.

    :param seeds: [(namespace, tablename), ...]

    :returns: (tables, sequences)
    """
    # Results
    tables = set()
    sequences = set()

    # Our pending set to check
    pending_tables = set(seeds)

    # Generate the set of tables that reference the seed directly
    # or indirectly via foreign key constraints, including the seed itself.
    while pending_tables:
        namespace, tablename = pending_tables.pop()
        tables.add((namespace, tablename))
        # Find all tables that reference the current (seed) table
        # and all tables that the seed table references.
        cur.execute("""
            SELECT ref_namespace.nspname, ref_class.relname
            FROM
                -- One of the seed tables
                pg_class AS seed_class,
                pg_namespace AS seed_namespace,

                -- A table referencing the seed, or being referenced by
                -- the seed.
                pg_class AS ref_class,
                pg_namespace AS ref_namespace,

                pg_constraint
            WHERE
                seed_class.relnamespace = seed_namespace.oid
                AND ref_class.relnamespace = ref_namespace.oid

                AND seed_namespace.nspname = %s
                AND seed_class.relname = %s

                -- Foreign key constraints are all we care about.
                AND pg_constraint.contype = 'f'

                -- We want tables referenced by, or referred to, the
                -- seed table.
                AND ((pg_constraint.conrelid = ref_class.oid
                        AND pg_constraint.confrelid = seed_class.oid)
                    OR (pg_constraint.conrelid = seed_class.oid
                        AND pg_constraint.confrelid = ref_class.oid)
                    )
            """ % sqlvalues(namespace, tablename))
        for namespace, tablename in cur.fetchall():
            key = (namespace, tablename)
            if key not in tables and key not in pending_tables:
                pending_tables.add(key)

    # Generate the set of sequences that are linked to any of our set of
    # tables. We assume these are all sequences created by creation of
    # serial or bigserial columns, or other sequences OWNED BY a particular
    # column.
    for namespace, tablename in tables:
        cur.execute("""
            SELECT seq
            FROM (
                SELECT pg_get_serial_sequence(%s, attname) AS seq
                FROM pg_namespace, pg_class, pg_attribute
                WHERE pg_namespace.nspname = %s
                    AND pg_class.relnamespace = pg_namespace.oid
                    AND pg_class.relname = %s
                    AND pg_attribute.attrelid = pg_class.oid
                    AND pg_attribute.attisdropped IS FALSE
                ) AS whatever
            WHERE seq IS NOT NULL;
            """ % sqlvalues(fqn(namespace, tablename), namespace, tablename))
        for row in cur.fetchall():
            sequences.add(row[0])

    # We can't easily convert the sequence name to (namespace, name) tuples,
    # so we might as well convert the tables to dot notation for consistancy.
    tables = set(fqn(namespace, tablename) for namespace, tablename in tables)

    return tables, sequences


def discover_unreplicated(cur):
    """Inspect the database for tables and sequences in the public schema
    that are not in a replication set.
    
    :returns: (unreplicated_tables_set, unreplicated_sequences_set)
    """
    all_tables = all_tables_in_schema(cur, 'public')
    all_sequences = all_sequences_in_schema(cur, 'public')

    cur.execute("""
        SELECT tab_nspname, tab_relname FROM %s
        WHERE tab_nspname = 'public'
        """ % fqn(CLUSTER_NAMESPACE, "sl_table"))
    replicated_tables = set(fqn(*row) for row in cur.fetchall())

    cur.execute("""
        SELECT seq_nspname, seq_relname FROM %s
        WHERE seq_nspname = 'public'
        """ % fqn(CLUSTER_NAMESPACE, "sl_sequence"))
    replicated_sequences = set(fqn(*row) for row in cur.fetchall())

    return (
        all_tables - replicated_tables - IGNORED_TABLES,
        all_sequences - replicated_sequences)


class ReplicationConfigError(Exception):
    """Exception raised by validate_replication_sets() when our replication
    setup is misconfigured.
    """


def validate_replication(cur):
    """Raise a ReplicationSetupError if there is something wrong with
    our replication sets.

    This might include tables exist that are not in a replication set,
    or tables that exist in multiple replication sets for example.

    These is not necessarily limits with what Slony-I allows, but might
    be due to policies we have made (eg. a table allowed in just one
    replication set).
    """
    unrepl_tables, unrepl_sequences = discover_unreplicated(cur)
    if unrepl_tables:
        raise ReplicationConfigError(
            "Unreplicated tables: %s" % repr(unrepl_tables))
    if unrepl_sequences:
        raise ReplicationConfigError(
            "Unreplicated sequences: %s" % repr(unrepl_sequences))

    authdb_tables, authdb_sequences = calculate_replication_set(
        cur, AUTHDB_SEED)
    lpmain_tables, lpmain_sequences = calculate_replication_set(
        cur, LPMAIN_SEED)

    confused_tables = authdb_tables.intersection(lpmain_tables)
    if confused_tables:
        raise ReplicationConfigError(
            "Tables exist in multiple replication sets: %s"
            % repr(confused_tables))
    confused_sequences = authdb_sequences.intersection(lpmain_sequences)
    if confused_sequences:
        raise ReplicationConfigError(
            "Sequences exist in multiple replication sets: %s"
            % repr(confused_sequences))


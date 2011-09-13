#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Initialize the cluster.

This script is run once to convert a singledb Launchpad instance to
a replicated setup.
"""

import _pythonpath

from optparse import OptionParser
import subprocess
import sys

import helpers

from canonical.config import config
from canonical.database.sqlbase import connect, ISOLATION_LEVEL_AUTOCOMMIT
from canonical.database.postgresql import (
        all_sequences_in_schema, all_tables_in_schema, ConnectionString
        )
from canonical.launchpad.scripts import (
        logger, logger_options, db_options
        )

__metaclass__ = type
__all__ = []


log = None # Global logger, initialized in main()

options = None # Parsed command line options, initialized in main()

cur = None # Shared database cursor to the master, initialized in main()


def duplicate_schema():
    """Duplicate the master schema into the slaves."""
    log.info('Duplicating database schema')

    master_cs = ConnectionString(config.database.rw_main_master)
    slave1_cs = ConnectionString(config.database.rw_main_slave)

    # We can't use pg_dump to replicate security as not all of the roles
    # may exist in the slave databases' clusters yet.
    cmd = "pg_dump -x -s %s | psql -q %s" % (
        master_cs.asPGCommandLineArgs(), slave1_cs.asPGCommandLineArgs())
    log.debug('Running %s' % cmd)
    rv = subprocess.call(cmd, shell=True)
    if rv != 0:
        log.fatal("Schema duplication failed, pg_dump returned %d" % rv)
        sys.exit(rv)

    # Now setup security on the slaves and create any needed roles,
    log.info('Setting up security on slave')
    cmd = "../schema/security.py %s" % slave1_cs.asLPCommandLineArgs()
    log.debug("Running %s" % cmd)
    rv = subprocess.call(cmd.split())
    if rv != 0:
        print >> sys.stderr, "ERR: security setup failed, returning %d" % rv
        sys.exit(rv)


def initialize_cluster():
    """Initialize the cluster."""
    log.info('Initializing Slony-I cluster')
    master_connection_string = ConnectionString(
        config.database.rw_main_master)
    master_connection_string.user = 'slony'
    helpers.execute_slonik("""
        node 1 admin conninfo = '%s';
        try {
            echo 'Initializing cluster and Master node.';
            init cluster (id=1, comment='Master Node');
            }
        on success { echo 'Cluster initialized.'; }
        on error { echo 'Cluster initialization failed.'; exit 1; }
        """ % master_connection_string)


def ensure_live():
    log.info('Ensuring slon daemons are live and propagating events.')
    helpers.sync(120) # Will exit on failure.


def create_replication_sets(lpmain_tables, lpmain_sequences):
    """Create the replication sets."""
    log.info('Creating Slony-I replication sets.')

    script = ["try {"]

    entry_id = 1

    script.append("""
        echo 'Creating LPMain replication set (@lpmain_set)';
        create set (
            id=@lpmain_set, origin=@master_node,
            comment='Launchpad tables and sequences');
        """)

    script.append(
        "echo 'Adding %d tables to replication set @lpmain_set';"
        % len(lpmain_tables))
    for table in sorted(lpmain_tables):
        script.append("""
            set add table (
                set id=@lpmain_set,
                origin=@master_node,
                id=%(entry_id)d,
                fully qualified name='%(table)s');
            """ % vars())
        entry_id += 1

    entry_id = 1
    script.append(
        "echo 'Adding %d sequences to replication set @lpmain_set';"
        % len(lpmain_sequences))
    for sequence in sorted(lpmain_sequences):
        script.append("""
            set add sequence (
                set id=@lpmain_set,
                origin=@master_node,
                id=%(entry_id)d,
                fully qualified name='%(sequence)s');
            """ % vars())
        entry_id += 1

    script.append("""
        }
        on error { echo 'Failed.'; exit 1; }
        """)
    helpers.execute_slonik('\n'.join(script), sync=600)

    helpers.validate_replication(cur) # Explode now if we have messed up.


def main():
    parser = OptionParser()
    db_options(parser)
    logger_options(parser)

    parser.set_defaults(dbuser='slony')

    global options
    options, args = parser.parse_args()

    global log
    log = logger(options)

    # Generate lists of sequences and tables for our replication sets.
    log.debug("Connecting as %s" % options.dbuser)
    con = connect()
    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    global cur
    cur = con.cursor()
    log.debug("Calculating lpmain replication set.")
    lpmain_tables, lpmain_sequences = helpers.calculate_replication_set(
        cur, helpers.LPMAIN_SEED)

    # Sanity check these lists - we want all objects in the public
    # schema to be in one and only one replication set.
    log.debug("Performing sanity checks.")
    fails = 0
    for table in all_tables_in_schema(cur, 'public'):
        times_seen = 0
        for table_set in [lpmain_tables, helpers.IGNORED_TABLES]:
            if table in table_set:
                times_seen += 1
        if times_seen == 0:
            log.error("%s not in any replication set." % table)
            fails += 1
        if times_seen > 1:
            log.error("%s is in multiple replication sets." % table)
            fails += 1
    for sequence in all_sequences_in_schema(cur, 'public'):
        times_seen = 0
        for sequence_set in [lpmain_sequences, helpers.IGNORED_SEQUENCES]:
            if sequence in sequence_set:
                times_seen += 1
        if times_seen == 0:
            log.error("%s not in any replication set." % sequence)
            fails += 1
        if times_seen > 1:
            log.error("%s is in multiple replication sets." % sequence)
            fails += 1
    if fails > 0:
        log.fatal("%d errors in replication set definitions." % fails)
        sys.exit(1)

    initialize_cluster()

    ensure_live()

    create_replication_sets(lpmain_tables, lpmain_sequences)

    helpers.sync(0)


if __name__ == '__main__':
    sys.exit(main())

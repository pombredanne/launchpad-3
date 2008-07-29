#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Initialize the cluster."""

import _pythonpath

from optparse import OptionParser
import subprocess
import sys

import helpers

from canonical.database.sqlbase import cursor
from canonical.database.postgresql import (
        all_sequences_in_schema, all_tables_in_schema, replication_set,
        )
from canonical.launchpad.scripts import (
        execute_zcml_for_scripts, logger, logger_options,
        )

__metaclass__ = type
__all__ = []


def main():
    parser = OptionParser()
    #db_options(parser)
    logger_options(parser)

    options, args = parser.parse_args()

    log = logger(options)

    execute_zcml_for_scripts()

    # Confirm each database exists and is connectable.

    # Confirm the slave databases are empty.

    # Create the 'slony' superuser in each database if it does not already
    # exist.

    # Change our connection to use the 'slony' user from this point on.

    # Duplicate the master schema into the slaves, except for security.
    # We can't use pg_dump to replicate security as not all of the roles
    # may exist in the slave databases' clusters yet.
    log.info('Duplicating database schema')
    rv = subprocess.call(
        "pg_dump -x -s -U slony launchpad_dev "
        "| psql -q -U slony launchpad_dev_slave1", shell=True)
    if rv != 0:
        print >> sys.stderr, "ERR: Schema dumplcation returned %d" % rv
        sys.exit(rv)

    # Generate lists of sequences and tables for our replication sets.
    cur = cursor()
    authdb_tables, authdb_sequences = replication_set(
            cur, [
                ('public', 'account'),
                ('public', 'openidassociations'),
                ])
    lpmain_tables, lpmain_sequences = replication_set(
            cur, [
                ('public', 'person'),
                ('public', 'launchpaddatabaserevision'),
                ('public', 'fticache'),
                ('public', 'nameblacklist'),
                ('public', 'codeimportmachine'),
                ('public', 'scriptactivity'),
                ('public', 'standardshipitrequest'),
                ('public', 'bugtag'),
                ('public', 'launchpadstatistic'),
                ('public', 'packagebugsupervisor'), # Dud fk definition!
                ])
    # These tables will exist in a developer's database and should
    # be ignored.
    session_tables = set(
            ['public.secret', 'public.sessiondata', 'public.sessionpkgdata'])

    # Sanity check these lists - we want all objects in the public
    # schema to be in one and only one replication set.
    fails = 0
    for table in all_tables_in_schema(cur, 'public'):
        times_seen = 0
        for table_set in [authdb_tables, lpmain_tables, session_tables]:
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
        for sequence_set in [authdb_sequences, lpmain_sequences]:
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

    # Now setup security on the slaves and create any needed roles,
    log.info('Setting up security on slave')
    rv = subprocess.call([
        "../schema/security.py",  "-d", "launchpad_dev"])
    if rv != 0:
        print >> sys.stderr, "ERR: security setup failed, returning %d" % rv
        sys.exit(rv)

    # Initialize the cluster.
    log.info('Initializing Slony-I cluster')
    helpers.execute_slonik("""
        try {
            echo 'Initializing cluster and Master node.';
            init cluster (id=@master_id, comment='Master Node');
            }
        on success { echo 'Cluster initialized.'; }
        on error { echo 'Cluster initialization failed.'; exit 1; }
        """)
    helpers.execute_slonik("""
        try {
            echo 'Initializing Slave#1 node.';
            store node (id=@slave1_id, comment='Slave Node #1');

            echo 'Storing Master -> Slave#1 path.';
            store path (
                server=@master_id, client=@slave1_id,
                conninfo=@master_conninfo);

            echo 'Storing Slave#1 -> Master path.';
            store path (
                server=@slave1_id, client=@master_id,
                conninfo=@slave1_conninfo);
            }
        on success { echo 'Slave#1 initialized.'; }
        on error { echo 'Slave#1 initialization failed.'; exit 1; }
        """)

    log.info('Ensuring slon daemons are live and propagating events.')
    helpers.sync()

    # Create the replication sets
    log.info('Creating Slony-I replication sets.')
    script = ["""
        try {
        echo 'Creating AuthDB replication set (@authdb_set_id)';
        create set (
            id=@authdb_set_id, origin=@master_id,
            comment='AuthDB tables and sequences');
        """]

    entry_id = 1
    for table in authdb_tables:
        script.append("""
            echo 'Adding %(table)s to replication set @authdb_set_id';
            set add table (
                set id=@authdb_set_id,
                origin=@master_id,
                id=%(entry_id)d,
                fully qualified name='%(table)s');
            """ % vars())
        entry_id += 1
    for sequence in authdb_sequences:
        script.append("""
            echo 'Adding %(sequence)s to replication set @authdb_set_id';
            set add sequence (
                set id=@authdb_set_id,
                origin=@master_id,
                id=%(entry_id)d,
                fully qualified name='%(sequence)s');
            """ % vars())
        entry_id += 1

    entry_id += 100
    script.append("""
        echo 'Creating LPMain replication set (@lpmain_set_id)';
        create set (
            id=@lpmain_set_id, origin=@master_id,
            comment='Launchpad tables and sequences');
        """)

    for table in lpmain_tables:
        script.append("""
            echo 'Adding %(table)s to replication set @lpmain_set_id';
            set add table (
                set id=@lpmain_set_id,
                origin=@master_id,
                id=%(entry_id)d,
                fully qualified name='%(table)s');
            """ % vars())
        entry_id += 1
    for sequence in lpmain_sequences:
        script.append("""
            echo 'Adding %(sequence)s to replication set @lpmain_set_id';
            set add sequence (
                set id=@lpmain_set_id,
                origin=@master_id,
                id=%(entry_id)d,
                fully qualified name='%(sequence)s');
            """ % vars())
        entry_id += 1

    script.append("""
        }
        on error { echo 'Failed.'; exit 1; }
        echo 'Syncing';
        sync (id=1);
        wait for event(origin=ALL, CONFIRMED=ALL);
        """)
    helpers.execute_slonik('\n'.join(script), sync=600)

    # Generate and run a slonik script subscribing the slave databases
    # to replication set #1.
    log.info('Subscribing slaves to replication sets.')
    helpers.execute_slonik("""
        subscribe set (
            id=@authdb_set_id,
            provider=@master_id, receiver=@slave1_id,
            forward=no);
        subscribe set (
            id=@lpmain_set_id,
            provider=@master_id, receiver=@slave1_id,
            forward=no);
        """)
    log.info('Waiting for synchronization.')
    helpers.execute_slonik("""
        sync (id=1);
        wait for event (
            origin=@master_id, confirmed=@slave1_id, wait on=@master_id);
        """)


if __name__ == '__main__':
    sys.exit(main())

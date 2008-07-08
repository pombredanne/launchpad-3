#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Initialize the cluster."""

import _pythonpath

from optparse import OptionParser
import subprocess
import sys

import helpers

from canonical.database.sqlbase import cursor
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
        init cluster (id=@master_id, comment='Master Node');
        """)

    # Initialize the slave nodes
    log.info('Initializing Slony-I slave nodes')
    helpers.execute_slonik("""
        store node (id=@slave1_id, comment='Slave Node #1');
        store path (
            server=@master_id, client=@slave1_id, conninfo=@master_conninfo);
        store path (
            server=@slave1_id, client=@master_id, conninfo=@slave1_conninfo);
        """)

    # Create the replication sets
    log.info('Creating Slony-I replication sets.')
    script = ["""
        create set (id=@authdb_set_id, origin=1,
            comment='AuthDB tables and sequences');
        create set (id=@lpmain_set_id, origin=1,
            comment='Launchpad tables and sequences');
        """]

    # All tables in 'public'
    cur = cursor()
    cur.execute("""
        SELECT nspname, relname
        FROM pg_class, pg_namespace
        WHERE relnamespace=pg_namespace.oid AND nspname='public'
            AND relkind='r'
            AND relname NOT IN ('secret', 'sessiondata', 'sessionpkgdata')
        ORDER BY nspname, relname
        """)
    table_id = 1
    for namespace, tablename in cur.fetchall():
        script.append("""
            set add table (set id=@lpmain_set_id, origin=@master_id, id=%d,
                fully qualified name='%s.%s');
            """ % (table_id, namespace, tablename))
        table_id += 1

    # All sequences in 'public'
    cur.execute("""
        SELECT nspname, relname
        FROM pg_class, pg_namespace
        WHERE relnamespace=pg_namespace.oid AND nspname='public'
            AND relkind='S'
        ORDER BY nspname, relname
        """)
    sequence_id = 1
    for namespace, sequencename in cur.fetchall():
        script.append("""
            set add sequence (set id=@lpmain_set_id, origin=@master_id, id=%d,
                fully qualified name='%s.%s');
            """ % (sequence_id, namespace, sequencename))
        sequence_id += 1

    helpers.execute_slonik('\n'.join(script))

    # Generate and run a slonik script subscribing the slave databases
    # to replication set #1.
    log.info('Subscribing slaves to replication sets')
    helpers.execute_slonik("""
        subscribe set (
            id=@lpmain_set_id,
            provider=@master_id, receiver=@slave1_id,
            forward=no);
        """)

if __name__ == '__main__':
    sys.exit(main())

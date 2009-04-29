#!/usr/bin/python2.4
# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Populate the auth replication set.

This script moves the the SSO tables from the main replication set to
the auth replication set.

Once it has been run on production, these tables can no longer be
maintained using the Launchpad database maintenance scripts
(upgrade.py, security.py etc.).

We do this so Launchpad database upgrades do not lock the SSO tables,
allowing the SSO service to continue to operate.

This is a single shot script.
"""

__metaclass__ = type
__all__ = []

import _pythonpath

import sys
from textwrap import dedent
from optparse import OptionParser

from canonical.database.sqlbase import (
    connect, ISOLATION_LEVEL_AUTOCOMMIT, sqlvalues)
from canonical.launchpad.scripts import db_options, logger_options, logger

import replication.helpers

def create_auth_set(cur):
    """Create the auth replication set if it doesn't already exist."""
    cur.execute("SELECT TRUE FROM _sl.sl_set WHERE set_id=2")
    if cur.fetchone() is not None:
        log.info("Auth set already exists.")
        return
    slonik_script = dedent("""\
        create set (
            id=@authdb_set, origin=@master_node,
            comment='SSO service tables');
        """)
    log.info("Creating authdb replication set.")
    replication.helpers.execute_slonik(slonik_script, sync=0)


def subscribe_auth_set(cur):
    """The authdb set subscription much match the lpmain set subscription.

    This is a requirement to move stuff between replication sets. It
    is also what we want (all nodes replicating everything).
    """
    cur.execute("""
        SELECT sub_receiver FROM _sl.sl_subscribe WHERE sub_set = 1
        EXCEPT
        SELECT sub_receiver FROM _sl.sl_subscribe WHERE sub_set = 2
        """)
    for node_id in (node_id for node_id, in cur.fetchall()):
        log.info("Subscribing Node #%d to authdb replication set" % node_id)
        success = replication.helpers.execute_slonik(dedent("""\
            subscribe set (
                id = @authdb_set, provider = @master_node,
                receiver = %d, forward = yes);
            """ % node_id), sync=0)
        if not success:
            log.error("Slonik failed. Exiting.")
            sys.exit(1)


def migrate_tables_and_sequences(cur):
    auth_tables, auth_sequences = (
        replication.helpers.calculate_replication_set(
            cur, replication.helpers.AUTHDB_SEED))

    slonik_script = ["try {"]
    for table_fqn in auth_tables:
        namespace, table_name = table_fqn.split('.')
        cur.execute("""
            SELECT tab_id, tab_set
            FROM _sl.sl_table
            WHERE tab_nspname = %s AND tab_relname = %s
            """ % sqlvalues(namespace, table_name))
        try:
            table_id, set_id = cur.fetchone()
        except IndexError:
            log.error("Table %s not found in _sl.sl_tables" % table_fqn)
            sys.exit(1)
        if set_id == 1:
            slonik_script.append("echo 'Moving table %s';" % table_fqn)
            slonik_script.append(
                "set move table "
                "(origin=@master_node, id=%d, new set=@authdb_set);"
                % table_id)
        elif set_id == 2:
            log.warn(
                "Table %s already in authdb replication set"
                % table_fqn)
        else:
            log.error("Unknown replication set %s" % set_id)
            sys.exit(1)

    for sequence_fqn in auth_sequences:
        namespace, sequence_name = sequence_fqn.split('.')
        cur.execute("""
            SELECT seq_id, seq_set
            FROM _sl.sl_sequence
            WHERE seq_nspname = %s AND seq_relname = %s
            """ % sqlvalues(namespace, sequence_name))
        try:
            sequence_id, set_id = cur.fetchone()
        except IndexError:
            log.error(
                "Sequence %s not found in _sl.sl_sequences" % sequence_fqn)
            sys.exit(1)
        if set_id == 1:
            slonik_script.append("echo 'Moving sequence %s';" % sequence_fqn)
            slonik_script.append(
                "set move sequence "
                "(origin=@master_node, id=%d, new set=@authdb_set);"
                % sequence_id)
        elif set_id ==2:
            log.warn(
                "Sequence %s already in authdb replication set."
                % sequence_fqn)
        else:
            log.error("Unknown replication set %s" % set_id)
            sys.exit(1)

    if len(slonik_script) == 1:
        log.warn("No tables or sequences to migrate.")
        return

    slonik_script.append(dedent("""\
        } on error {
            echo 'Failed to move one or more tables or sequences.';
            exit 1;
        }
        """))

    slonik_script = "\n".join(slonik_script)

    log.info("Running migration script...")
    if not replication.helpers.execute_slonik(slonik_script, sync=0):
        log.error("Slonik failed. Exiting.")
        sys.exit(1)


def main():
    parser = OptionParser()
    db_options(parser)
    logger_options(parser)
    options, args = parser.parse_args()

    global log
    log = logger(options)

    con = connect('slony', isolation=ISOLATION_LEVEL_AUTOCOMMIT)
    cur = con.cursor()

    # Don't start until cluster is synced.
    log.info("Waiting for sync.")
    replication.helpers.sync(0)

    create_auth_set(cur)
    subscribe_auth_set(cur)
    migrate_tables_and_sequences(cur)


log = None # Global log


if __name__ == '__main__':
    main()

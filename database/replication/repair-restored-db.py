#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Remove the broken Slony-I information from database populated by
pg_restore(1).

When you dump a database using pg_dump(1), the Slony-I install is dumped
too. After restoring this dump, you have a non-functional Slony-I
installation. If you are recovering the database for disaster recovery
purposes, you can keep the current install by repairing it using the
slonik(1) command REPAIR CONFIG. In other cases, you need to remove
Slony-I from the database (eg. building a staging database, we need
to install replication fresh.). This script does this procedure.
"""

__metaclass__ = type
__all__ = []

import _pythonpath

from optparse import OptionParser
import sys

import psycopg2

from canonical.config import config
from canonical.database.postgresql import ConnectionString
from canonical.database.sqlbase import (
    connect, quote, ISOLATION_LEVEL_AUTOCOMMIT)
from canonical.launchpad.scripts import db_options, logger_options, logger

import replication.helpers


def main():
    parser = OptionParser()
    db_options(parser)
    logger_options(parser)

    parser.set_defaults(dbuser='slony')

    options, args = parser.parse_args()

    log = logger(options)

    con = connect(isolation=ISOLATION_LEVEL_AUTOCOMMIT)

    if not replication.helpers.slony_installed(con):
        log.info("Slony-I not installed. Nothing to do.")
        return 0

    if not repair_with_slonik(log, options, con):
        repair_with_drop_schema(log, con)

    return 0


def repair_with_slonik(log, options, con):
    """Attempt to uninstall Slony-I via 'UNINSTALL NODE' per best practice.

    Returns True on success, False if unable to do so for any reason.
    """
    cur = con.cursor()

    # Determine the node id the database thinks it is.
    try:
        cmd = "SELECT %s.getlocalnodeid(%s)" % (
            replication.helpers.CLUSTER_NAMESPACE,
            quote(replication.helpers.CLUSTER_NAMESPACE))
        cur.execute(cmd)
        node_id = cur.fetchone()[0]
        log.debug("Node Id is %d" % node_id)

        # Get a list of set ids in the database.
        cur.execute(
            "SELECT DISTINCT set_id FROM %s.sl_set"
            % replication.helpers.CLUSTER_NAMESPACE)
        set_ids = set(row[0] for row in cur.fetchall())
        log.debug("Set Ids are %s" % repr(set_ids))

    except psycopg2.InternalError:
        # Not enough information to determine node id. Possibly
        # this is an empty database.
        log.debug('Broken or no Slony-I install.')
        return False

    connection_string = ConnectionString(config.database.rw_main_master)
    if options.dbname:
        connection_string.dbname = options.dbname
    if options.dbuser:
        connection_string.user = options.dbuser
    if options.dbhost:
        connection_string.host = options.dbhost

    script = [
        "cluster name = %s;" % replication.helpers.CLUSTERNAME,
        "node %d admin conninfo = '%s';" % (node_id, connection_string),
        ]
    for set_id in set_ids:
        script.append(
            "repair config (set id=%d, event node=%d, execute only on=%d);"
            % (set_id, node_id, node_id))
    script.append("uninstall node (id=%d);" % node_id)
    for line in script:
        log.debug(line)
    script = '\n'.join(script)

    return replication.helpers.execute_slonik(
        script, auto_preamble=False, exit_on_fail=False)


def repair_with_drop_schema(log, con):
    """
    Just drop the _sl schema as it is 'good enough' with Slony-I 1.2.

    This mechanism fails with Slony added primary keys, but we don't
    do that.
    """
    log.info('Fallback mode - dropping _sl schema.')
    cur = con.cursor()
    cur.execute("DROP SCHEMA _sl CASCADE")
    return True


if __name__ == '__main__':
    sys.exit(main())

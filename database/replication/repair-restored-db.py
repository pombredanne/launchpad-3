#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

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

import replication.helpers

from canonical.config import config
from canonical.database.postgresql import ConnectionString
from canonical.database.sqlbase import connect, sqlvalues
from canonical.launchpad.scripts import db_options, logger_options, logger

def main():
    parser = OptionParser()
    db_options(parser)
    logger_options(parser)
    options, args = parser.parse_args()

    log = logger(options)

    con = connect(options.dbuser)

    if not replication.helpers.slony_installed(con):
        log.info("Slony-I not installed. Nothing to do.")
        return 0

    cur = con.cursor()

    # Determine the node id the database thinks it is.
    cur.execute("SELECT _sl.getlocalnodeid('_sl')")
    node_id = cur.fetchone()[0]
    log.debug("Node Id is %d" % node_id)

    # Get a list of set ids in the database.
    cur.execute("SELECT DISTINCT set_id FROM _sl.sl_set")
    set_ids = set(row[0] for row in cur.fetchall())
    log.debug("Set Ids are %s" % repr(set_ids))

    # Close so we don't block slonik(1)
    del cur
    con.close()

    connection_string = ConnectionString(config.database.main_master)
    if options.dbname:
        connection_string.dbname = options.dbname
    if options.dbuser:
        connection_string.user = options.dbuser
    if options.dbhost:
        connection_string.host = options.dbhost

    script = [
        "cluster name = sl;",
        "node 1 admin conninfo = '%s';" % connection_string,
        ]
    for set_id in set_ids:
        script.append(
            "repair config (set id=%d, event node=%d, execute only on=%d);"
            % (set_id, node_id, node_id))
    script.append("uninstall node (id=%d);" % node_id)
    script = '\n'.join(script)
    print script

    replication.helpers.execute_slonik(script, auto_preamble=False)

if __name__ == '__main__':
    sys.exit(main())

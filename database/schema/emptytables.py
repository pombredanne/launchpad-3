#!/usr/bin/python2.4
# Copyright 2006 Canonical Ltd.  All rights reserved.

"""List empty database tables."""

__metaclass__ = type

import _pythonpath
from optparse import OptionParser

from canonical.database.sqlbase import connect
from canonical.launchpad.scripts import db_options
from fti import quote_identifier

def main(options):
    con = connect(options.dbuser)
    cur = con.cursor()
    cur.execute("""
        SELECT relname FROM pg_class,pg_namespace
        WHERE pg_class.relnamespace = pg_namespace.oid
            AND pg_namespace.nspname='public'
            AND pg_class.relkind = 'r'
        ORDER BY relname
        """)
    for table in (row[0] for row in cur.fetchall()):
        cur.execute(
                "SELECT TRUE FROM public.%s LIMIT 1" % quote_identifier(table)
                )
        if cur.fetchone() is None:
            print table


if __name__ == '__main__':
    parser = OptionParser()
    db_options(parser)
    (options, args) = parser.parse_args()

    main(options)

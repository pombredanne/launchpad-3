#!/usr/bin/python2.4
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""
The sampledata does not update the current values of all the sequences
used to populate the primary keys (this was removed to aid in merging changes
to the sampledata).

This script resets all of these sequences to the correct value based on the
maximum value currently found in the corresponding table.
"""

__metaclass__ = type

import sys, os, os.path
sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'lib')
        )

from optparse import OptionParser
from canonical.database.postgresql import resetSequences
from canonical.database.sqlbase import connect

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option(
            "-d", "--dbname", dest="dbname", help="database name",
            )
    (options, args) = parser.parse_args()
    if args:
        parser.error("Too many options given")
    if not options.dbname:
        parser.error("Required option --dbname not given")
    con = connect(None, options.dbname)
    resetSequences(con.cursor())
    con.commit()


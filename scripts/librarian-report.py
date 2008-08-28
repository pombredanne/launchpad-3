#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Report a breakdown of Librarian disk space usage."""

__metaclass__ = type
__all__ = []

import _pythonpath

import sys

from canonical.database.sqlbase import connect, quoteIdentifier
from canonical.database.postgresql import listReferences


def main():
    con = connect('')
    cur = con.cursor()

    # Collect direct references to the LibraryFileAlias table.
    references = set(
        (from_tab, from_col)
        for from_tab, from_col, to_tab, to_col, update, delete
            in listReferences(cur, 'libraryfilealias', 'id')
        if to_tab == 'libraryfilealias'
        )

    totals = set()
    for ref_tab, ref_col in sorted(references):
        q_ref_tab = quoteIdentifier(ref_tab)
        q_ref_col = quoteIdentifier(ref_col)
        cur.execute("""
            SELECT
                COALESCE(SUM(filesize), 0),
                pg_size_pretty(COALESCE(SUM(filesize), 0)),
                COUNT(*)
            FROM LibraryFileContent, LibraryFileAlias, %(q_ref_tab)s
            WHERE LibraryFileContent.id = LibraryFileAlias.content
                AND %(q_ref_tab)s.%(q_ref_col)s = LibraryFileContent.id
            """ % vars())
        total_bytes, formatted_size, num_files = cur.fetchone()
        totals.add((total_bytes, ref_tab, formatted_size, num_files))

    for total_bytes, tab_name, formatted_size, num_files in sorted(
        totals, reverse=True):
        print '%-10s %s in %d files' % (formatted_size, tab_name, num_files)

    return 0


if __name__ == '__main__':
    sys.exit(main())

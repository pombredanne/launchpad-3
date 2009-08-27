#!/usr/bin/python2.4
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

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
        (from_table, from_column)
        # Note that listReferences is recursive, which we don't
        # care about in this simple report. We also ignore the
        # irrelevant constraint type update and delete flags.
        for from_table, from_column, to_table, to_column, update, delete
            in listReferences(cur, 'libraryfilealias', 'id')
        if to_table == 'libraryfilealias'
        )

    totals = set()
    for referring_table, referring_column in sorted(references):
        quoted_referring_table = quoteIdentifier(referring_table)
        quoted_referring_column = quoteIdentifier(referring_column)
        cur.execute("""
            SELECT
                COALESCE(SUM(filesize), 0),
                pg_size_pretty(COALESCE(SUM(filesize), 0)),
                COUNT(*)
            FROM (
                SELECT DISTINCT ON (LFC.id) LFC.id, LFC.filesize
                FROM LibraryFileContent AS LFC, LibraryFileAlias AS LFA, %s
                WHERE LFC.id = LFA.content
                    AND LFA.id = %s.%s
                    AND LFC.deleted IS FALSE
                    AND (
                        LFA.expires IS NULL
                        OR LFA.expires > CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
                ORDER BY LFC.id
                ) AS Whatever
            """ % (
                quoted_referring_table, quoted_referring_table,
                quoted_referring_column))
        total_bytes, formatted_size, num_files = cur.fetchone()
        totals.add((total_bytes, referring_table, formatted_size, num_files))

    for total_bytes, tab_name, formatted_size, num_files in sorted(
        totals, reverse=True):
        print '%-10s %s in %d files' % (formatted_size, tab_name, num_files)

    return 0


if __name__ == '__main__':
    sys.exit(main())

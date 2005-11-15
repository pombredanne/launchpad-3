# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Librarian garbage collection routines"""

__metaclass__ = type

from canonical.database.sqlbase import cursor

log = None

def merge_duplicates(ztm):
    """Merge duplicate LibraryFileContent rows"""

    while True:
        ztm.begin()

        cur = cursor()
        cur.execute("""
            SELECT sha1, filesize
            FROM LibraryFileContent
            GROUP BY sha1, filesize
            HAVING COUNT(*) > 1
            LIMIT 1
            """)
        row = cur.fetchone()

        if row is None:
            # No more duplicates, so exit loop
            break

        sha1, filesize = cur.fetchone()

        # Get a list of our dupes, making sure that the first in the
        # list is not deleted if possible.
        cur.execute("""
            SELECT id
            FROM LibraryFileContent
            WHERE sha1=%(sha1) AND filesize=%(filesize)s
            ORDER BY deleted, datecreated
            """, vars())
        dupes = [row[0] for row in cur.fetchall()]

        log.info(
                "Found duplicate LibraryFileContents %s",
                ' '.join(dupes)
                )

        # Update all the LibraryFileAlias entries to point to a single
        # LibraryFileContent
        prime_id = dupes[0]
        other_ids = ', '.join(dupes[1:])
        log.debug(
                "Making LibraryFileAliases referencing %s reference %s instead",
                other_ids, prime_id
                )
        cur.execute("""
            UPDATE LibraryFileAlias SET content=%(prime_id)s
            WHERE content in (%(dupe_ids)s)
            """)

        log.debug("Committing")
        ztm.commit()


def delete_unreferenced_content(ztm):
    """Delete LibraryFileContent entries and their disk files that are
    not referenced by any LibraryFileAlias entries.
    """
    while True:
        cur.execute("""
            SELECT LibraryFileContent.id, deleted
            FROM LibraryFileContent
            LEFT OUTER JOIN LibraryFileAlias
                ON LibraryFileContent.id = LibraryFileAlias.content
            WHERE LibraryFileAlias.content IS NULL
            LIMIT 1
            """)

        # Delete old LibraryFileContent entries
        log.debug("Deleting LibraryFileContents %s", dupe_ids)
        cur.execute("""
            DELETE FROM LibraryFileContent WHERE id IN (%(dupe_ids)s)
            """, vars())

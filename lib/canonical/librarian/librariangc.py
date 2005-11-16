# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Librarian garbage collection routines"""

__metaclass__ = type

import os.path

from canonical.config import config
from canonical.database.sqlbase import cursor
from canonical.librarian.storage import _relFileLocation as relative_file_path

log = None

def merge_duplicates(ztm):
    """Merge duplicate LibraryFileContent rows"""

    # Get a list of all (sha1, filesize) that are duplicated in
    # LibraryFileContent
    ztm.begin()
    cur = cursor()
    cur.execute("""
        SELECT sha1, filesize
        FROM LibraryFileContent
        GROUP BY sha1, filesize
        HAVING COUNT(*) > 1
        """)
    rows = list(cur.fetchall())
    ztm.abort()

    # Merge the duplicate entries, each one in a seperate transaction
    for sha1, filesize in rows:
        ztm.begin()
        cur = cursor()

        sha1 = sha1.encode('US-ASCII') # Can't pass Unicode to execute (yet)

        # Get a list of our dupes, making sure that the first in the
        # list is not deleted if possible.
        cur.execute("""
            SELECT id
            FROM LibraryFileContent
            WHERE sha1=%(sha1)s AND filesize=%(filesize)s
            ORDER BY deleted, datecreated
            """, vars())
        dupes = [str(row[0]) for row in cur.fetchall()]

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
            WHERE content in (%(other_ids)s)
            """, vars())

        log.debug("Committing")
        ztm.commit()


def delete_unreferenced_content(ztm):
    """Delete LibraryFileContent entries and their disk files that are
    not referenced by any LibraryFileAlias entries.

    Note that a LibraryFileContent can only be accessed through a
    LibraryFileAlias, so all entries in this state are garbage no matter
    what their expires flag says.
    """
    ztm.begin()
    cur = cursor()
    cur.execute("""
        SELECT LibraryFileContent.id
        FROM LibraryFileContent
        LEFT OUTER JOIN LibraryFileAlias
            ON LibraryFileContent.id = LibraryFileAlias.content
        WHERE LibraryFileAlias.content IS NULL
        """)
    garbage_ids = [row[0] for row in cur.fetchall()]
    ztm.abort()

    for garbage_id in garbage_ids:
        # Remove the file from disk, if it hasn't already been
        path = get_file_path(garbage_id)
        if os.path.exists(path):
            log.info("Deleting %s", path)
            os.unlink(path)
        else:
            log.info("%s already deleted", path)

        ztm.begin()
        cur = cursor()
        # Delete old LibraryFileContent entries
        log.info("Deleting LibraryFileContent %d", garbage_id)
        cur.execute("""
            DELETE FROM LibraryFileContent WHERE id = %(garbage_id)s
            """, vars())
        ztm.commit()


def get_file_path(content_id):
    """Return the physical file path to the corresponding LibraryFileContent id
    """
    assert isinstance(content_id, int), 'Invalid content_id %r' % (content_id,)
    storage_root = config.librarian.server.root
    # Do a basic sanity check.
    if not os.path.isdir(os.path.join(storage_root, 'incoming')):
        raise RuntimeError(
                "Librarian file storage not found at %s" % storage_root
                )
    path = os.path.join(
            storage_root, relative_file_path(content_id)
            )
    return path


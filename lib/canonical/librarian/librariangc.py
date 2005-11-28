# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Librarian garbage collection routines"""

__metaclass__ = type

import sys
import os.path

from canonical.config import config
from canonical.database.sqlbase import cursor
from canonical.librarian.storage import _relFileLocation as relative_file_path
from canonical.librarian.storage import _sameFile
from canonical.database.postgresql import listReferences

log = None

def merge_duplicates(ztm):
    """Merge duplicate LibraryFileContent rows
    
    This is the first step in a full garbage collection run. We assume files
    are identical if their sha1 hashes and filesizes are identical. For every
    duplicate detected, we make all LibraryFileAlias entries point to one of
    them and delete the unnecessary duplicates from the filesystem and the
    database.
    """

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
        # list is not deleted if possible. Where multiple non-deleted
        # files exist, we return the most recently added one first, because
        # this is the version most likely to exist on the staging server
        # (it should be irrelevant on production).
        cur.execute("""
            SELECT id
            FROM LibraryFileContent
            WHERE sha1=%(sha1)s AND filesize=%(filesize)s
            ORDER BY deleted, datecreated DESC
            """, vars())
        dupes = [str(row[0]) for row in cur.fetchall()]

        log.info(
                "Found duplicate LibraryFileContents %s",
                ' '.join(dupes)
                )

        # Make sure the first file exists on disk. Don't merge if it
        # doesn't. This shouldn't happen on production, so we don't try
        # and cope - just report and skip. However, on staging this will
        # be more common because database records has been synced from
        # production but the actual librarian contents has not.
        dupe1_id = int(dupes[0])
        dupe1_path = get_file_path(dupe1_id)
        if not os.path.exists(dupe1_path):
            if config.name == 'staging':
                log.debug(
                        "LibraryFileContent %d data is missing (%s)",
                        dupe1_id, dupe1_path
                        )
            else:
                log.error(
                        "LibraryFileContent %d data is missing (%s)",
                        dupe1_id, dupe1_path
                        )
            ztm.abort()
            continue

        # Do a manual check that they really are identical, because we
        # employ paranoids. And we might as well cope with someone breaking
        # SHA1 enough that it becomes possible to create a SHA1 collision
        # with an identical filesize to an existing file. Which is pretty
        # unlikely. Where did I leave my tin foil hat?
        for dupe2_id in (int(dupe) for dupe in dupes[1:]):
            dupe2_path = get_file_path(dupe2_id)
            # Check paths exist, because on staging they may not!
            if (os.path.exists(dupe2_path)
                and not _sameFile(dupe1_path, dupe2_path)):
                log.error(
                        "SHA-1 collision found. LibraryFileContent %d and "
                        "%d have the same SHA1 and filesize, but are not "
                        "byte-for-byte identical.",
                        dupe1_id, dupe2_id
                        )
                ztm.abort()
                sys.exit(1)

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
            """ % vars())

        log.debug("Committing")
        ztm.commit()


def delete_unreferenced_aliases(ztm):
    """Delete unreferenced LibraryFileAliases and their LibraryFileContent

    This is the second step in a full garbage collection sweep. We determine
    which LibraryFileContent entries are not being referenced by other objects
    in the database. If we find one that is not reachable in any way, we
    remove all its corresponding LibraryFileAlias records from the database
    if they are all expired (expiry in the past or NULL), and none have been
    recently accessed (last_access over one week in the past).

    Note that *all* LibraryFileAliases referencing a given LibraryFileContent
    must be unreferenced for them to be deleted - a single reference will keep
    the whole set alive.
    """
    log.info("Deleting unreferenced LibraryFileAliases")

    # Generate a set of all our LibraryFileContent ids, except for ones
    # with expiry dates not yet reached (these lurk in the database until
    # expired) and those that have been accessed in the last week (currently
    # in use, so leave them lurking a while longer)
    ztm.begin()
    cur = cursor()
    cur.execute("""
        SELECT c.id
        FROM LibraryFileContent AS c, LibraryFileAlias AS a
        WHERE c.id = a.content
        GROUP BY c.id
        HAVING (max(expires) IS NULL OR max(expires)
                < CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - '1 week'::interval
                )
            AND (max(last_accessed) IS NULL OR max(last_accessed)
                < CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - '1 week'::interval
                )
        """)
    content_ids = set(row[0] for row in cur.fetchall())
    ztm.abort()
    log.info(
        "Found %d LibraryFileContent entries possibly unreferenced",
        len(content_ids)
        )

    # Determine what columns link to LibraryFileAlias
    ztm.begin()
    cur = cursor()
    # references = [(table, column), ...]
    references = [
        tuple(ref[:2]) for ref in listReferences(cur, 'libraryfilealias', 'id')
        ]
    assert len(references) > 10, 'Database introspection returned nonsense'
    ztm.abort()
    log.info("Found %d columns referencing LibraryFileAlias", len(references))

    # Remove all referenced LibraryFileContent ids from content_ids
    for table, column in references:
        ztm.begin()
        cur = cursor()
        cur.execute("""
            SELECT DISTINCT LibraryFileContent.id
            FROM LibraryFileContent, LibraryFileAlias, %(table)s
            WHERE LibraryFileContent.id = LibraryFileAlias.content
                AND LibraryFileAlias.id = %(table)s.%(column)s
            """ % vars())
        referenced_ids = set(row[0] for row in cur.fetchall())
        ztm.abort()
        log.debug(
                "Found %d distinct LibraryFileAlias references in %s(%s)",
                len(referenced_ids), table, column
                )
        content_ids.difference_update(referenced_ids)
        log.debug(
                "Now only %d LibraryFileContents possibly unreferenced",
                len(content_ids)
                )

    # Delete unreferenced LibraryFileAliases. Note that this will raise a
    # database exception if we screwed up and attempt to delete an alias that
    # is still referenced.
    for content_id in content_ids:
        ztm.begin()
        cur = cursor()
        # First a sanity check to ensure we aren't removing anything we
        # shouldn't be.
        cur.execute("""
            SELECT COUNT(*)
            FROM LibraryFileAlias
            WHERE content=%(content_id)s
                AND (
                    expires + '1 week'::interval
                        > CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                    OR last_accessed + '1 week'::interval
                        > CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                    )
            """, vars())
        assert cur.fetchone()[0] == 0, "Logic error - sanity check failed"
        log.info(
                "Deleting all LibraryFileAlias references to "
                "LibraryFileContent %d", content_id
                )
        cur.execute("""
            DELETE FROM LibraryFileAlias WHERE content=%(content_id)s
            """, vars())
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
        ztm.begin()
        cur = cursor()

        # Delete old LibraryFileContent entries. Note that this will fail
        # if we screwed up and still have LibraryFileAlias entries referencing
        # it.
        log.info("Deleting LibraryFileContent %d", garbage_id)
        cur.execute("""
            DELETE FROM LibraryFileContent WHERE id = %(garbage_id)s
            """, vars())

        # Remove the file from disk, if it hasn't already been
        path = get_file_path(garbage_id)
        if os.path.exists(path):
            log.info("Deleting %s", path)
            os.unlink(path)
        else:
            log.info("%s already deleted", path)

        # And commit the database changes. It may be possible for this to
        # fail in rare cases, leaving a record in the DB with no corresponding
        # file on disk, but that is OK as it will all be tidied up next run,
        # and the file is unreachable anyway so nothing will attempt to
        # access it between now and the next garbage collection run.
        ztm.commit()


def get_file_path(content_id):
    """Return the physical file path to the corresponding LibraryFileContent id
    """
    assert isinstance(content_id, (int, long)), 'Invalid content_id %r' % (
            content_id,
            )
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


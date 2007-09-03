# Copyright 2004-2006 Canonical Ltd.  All rights reserved.
"""Librarian garbage collection routines"""

__metaclass__ = type

from datetime import datetime, timedelta
import sys
from time import time
import os
import os.path

from canonical.config import config
from canonical.database.sqlbase import cursor
from canonical.librarian.storage import _relFileLocation as relative_file_path
from canonical.librarian.storage import _sameFile
from canonical.database.postgresql import listReferences

BATCH_SIZE = 1

log = None
debug = False

def confirm_no_clock_skew(con):
    """Raise an exception if there is significant clock skew between the
    database and this machine.

    It is theoretically possible to lose data if there is more than several
    hours of skew.
    """
    cur = con.cursor()
    cur.execute("SELECT CURRENT_TIMESTAMP AT TIME ZONE 'UTC'")
    db_now = cur.fetchone()[0]
    local_now = datetime.utcnow()
    five_minutes = timedelta(minutes=5)

    if -five_minutes < local_now - db_now < five_minutes:
        return
    else:
        raise Exception("%s clock skew between librarian and database" % (
            local_now - db_now,
            ))

def delete_expired_blobs(con):
    """Remove expired TemporaryBlobStorage entries and their corresponding
       LibraryFileAlias entries.

       We delete the LibraryFileAliases here as the default behavior of the
       garbage collector could leave them hanging around indefinitely.
    """
    cur = con.cursor()
    cur.execute("""
        SELECT file_alias
        INTO TEMPORARY TABLE BlobAliasesToDelete
        FROM LibraryFileAlias, TemporaryBlobStorage
        WHERE file_alias = LibraryFileAlias.id
            AND expires < CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
        """)
    cur.execute("""
        DELETE FROM TemporaryBlobStorage
        USING BlobAliasesToDelete
        WHERE TemporaryBlobStorage.file_alias = BlobAliasesToDelete.file_alias
        """)
    cur.execute("""
        DELETE FROM LibraryFileAlias
        USING BlobAliasesToDelete
        WHERE file_alias = LibraryFileAlias.id
        """)
    log.info("Removed %d expired blobs" % cur.rowcount)
    con.commit()


def merge_duplicates(con):
    """Merge duplicate LibraryFileContent rows

    This is the first step in a full garbage collection run. We assume files
    are identical if their sha1 hashes and filesizes are identical. For every
    duplicate detected, we make all LibraryFileAlias entries point to one of
    them and delete the unnecessary duplicates from the filesystem and the
    database.
    """

    # Get a list of all (sha1, filesize) that are duplicated in
    # LibraryFileContent
    cur = con.cursor()
    cur.execute("""
        SELECT sha1, filesize
        FROM LibraryFileContent
        GROUP BY sha1, filesize
        HAVING COUNT(*) > 1
        """)
    rows = list(cur.fetchall())

    # Merge the duplicate entries, each one in a seperate transaction
    for sha1, filesize in rows:
        cur = con.cursor()

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
        dupes = [row[0] for row in cur.fetchall()]

        if debug:
            log.debug("Found duplicate LibraryFileContents")
            # Spit out more info in case it helps work out where
            # dupes are coming from.
            for dupe_id in dupes:
                cur.execute("""
                    SELECT id, filename, mimetype FROM LibraryFileAlias
                    WHERE content = %(dupe_id)s
                    """, vars())
                for id, filename, mimetype in cur.fetchall():
                    log.debug("> %d %s %s" % (id, filename, mimetype))

        # Make sure the first file exists on disk. Don't merge if it
        # doesn't. This shouldn't happen on production, so we don't try
        # and cope - just report and skip. However, on staging this will
        # be more common because database records has been synced from
        # production but the actual librarian contents has not.
        dupe1_id = dupes[0]
        dupe1_path = get_file_path(dupe1_id)
        if not os.path.exists(dupe1_path):
            if config.name == 'staging':
                log.debug(
                        "LibraryFileContent %d data is missing (%s)",
                        dupe1_id, dupe1_path
                        )
            else:
                log.warning(
                        "LibraryFileContent %d data is missing (%s)",
                        dupe1_id, dupe1_path
                        )
            continue

        # Do a manual check that they really are identical, because we
        # employ paranoids. And we might as well cope with someone breaking
        # SHA1 enough that it becomes possible to create a SHA1 collision
        # with an identical filesize to an existing file. Which is pretty
        # unlikely. Where did I leave my tin foil hat?
        for dupe2_id in (dupe for dupe in dupes[1:]):
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
                sys.exit(1)

        # Update all the LibraryFileAlias entries to point to a single
        # LibraryFileContent
        prime_id = dupes[0]
        other_ids = ', '.join(str(dupe) for dupe in dupes[1:])
        log.debug(
                "Making LibraryFileAliases referencing %s reference %s instead",
                other_ids, prime_id
                )
        for other_id in dupes[1:]:
            cur.execute("""
                UPDATE LibraryFileAlias SET content=%(prime_id)s
                WHERE content = %(other_id)s
                """, vars())

        log.debug("Committing")
        con.commit()


def delete_unreferenced_aliases(con):
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
    cur = con.cursor()
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
    log.info(
        "Found %d LibraryFileContent entries possibly unreferenced",
        len(content_ids)
        )

    # Determine what columns link to LibraryFileAlias
    # references = [(table, column), ...]
    references = [
        tuple(ref[:2]) for ref in listReferences(cur, 'libraryfilealias', 'id')
        ]
    assert len(references) > 10, 'Database introspection returned nonsense'
    log.info("Found %d columns referencing LibraryFileAlias", len(references))

    # Remove all referenced LibraryFileContent ids from content_ids
    for table, column in references:
        cur.execute("""
            SELECT DISTINCT LibraryFileContent.id
            FROM LibraryFileContent, LibraryFileAlias, %(table)s
            WHERE LibraryFileContent.id = LibraryFileAlias.content
                AND LibraryFileAlias.id = %(table)s.%(column)s
            """ % vars())
        referenced_ids = set(row[0] for row in cur.fetchall())
        log.info(
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
    content_ids = list(content_ids)
    for i in range(0, len(content_ids), BATCH_SIZE):
        in_content_ids = ','.join(
                (str(content_id) for content_id in content_ids[i:i+BATCH_SIZE])
                )
        # First a sanity check to ensure we aren't removing anything we
        # shouldn't be.
        cur.execute("""
            SELECT COUNT(*)
            FROM LibraryFileAlias
            WHERE content in (%(in_content_ids)s)
                AND (
                    expires + '1 week'::interval
                        > CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                    OR last_accessed + '1 week'::interval
                        > CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                    )
            """ % vars())
        assert cur.fetchone()[0] == 0, "Logic error - sanity check failed"
        log.debug(
                "Deleting all LibraryFileAlias references to "
                "LibraryFileContents %s", in_content_ids
                )
        cur.execute("""
            DELETE FROM LibraryFileAlias WHERE content IN (%(in_content_ids)s)
            """ % vars())
        con.commit()


def delete_unreferenced_content(con):
    """Delete LibraryFileContent entries and their disk files that are
    not referenced by any LibraryFileAlias entries.

    Note that a LibraryFileContent can only be accessed through a
    LibraryFileAlias, so all entries in this state are garbage no matter
    what their expires flag says.
    """
    cur = con.cursor()
    cur.execute("""
        SELECT LibraryFileContent.id
        FROM LibraryFileContent
        LEFT OUTER JOIN LibraryFileAlias
            ON LibraryFileContent.id = LibraryFileAlias.content
        WHERE LibraryFileAlias.content IS NULL
        """)
    garbage_ids = [row[0] for row in cur.fetchall()]

    for i in range(0, len(garbage_ids), BATCH_SIZE):
        in_garbage_ids = ','.join(
            (str(garbage_id) for garbage_id in garbage_ids[i:i+BATCH_SIZE])
            )

        # Delete old LibraryFileContent entries. Note that this will fail
        # if we screwed up and still have LibraryFileAlias entries referencing
        # it.
        log.debug("Deleting LibraryFileContents %s", in_garbage_ids)
        cur.execute("""
            DELETE FROM LibraryFileContent WHERE id in (%s)
            """ % in_garbage_ids)

        for garbage_id in garbage_ids[i:i+BATCH_SIZE]:
            # Remove the file from disk, if it hasn't already been
            path = get_file_path(garbage_id)
            if os.path.exists(path):
                log.debug("Deleting %s", path)
                os.unlink(path)
            else:
                log.info("%s already deleted", path)

        # And commit the database changes. It may be possible for this to
        # fail in rare cases, leaving a record in the DB with no corresponding
        # file on disk, but that is OK as it will all be tidied up next run,
        # and the file is unreachable anyway so nothing will attempt to
        # access it between now and the next garbage collection run.
        con.commit()


def delete_unwanted_files(con):
    """Delete files found on disk that have no corresponding record in the
    database or have been flagged as 'deleted' in the database.

    Files will only be deleted if they where created more than one day ago
    to avoid deleting files that have just been uploaded but have yet to have
    the database records committed.
    """
    cur = con.cursor()

    # Get the largest id in the database
    cur.execute("SELECT max(id) from LibraryFileContent")
    max_id = cur.fetchone()[0]

    # Build a set containing all stored LibraryFileContent ids
    # that we want to keep.
    cur.execute("""
        SELECT id FROM LibraryFileContent
        WHERE deleted IS FALSE OR datecreated
            > CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - '1 day'::interval
        """)
    all_ids = set(row[0] for row in cur.fetchall())

    count = 0
    for content_id in range(1, max_id+1):
        if content_id in all_ids:
            continue # Linked in the db - do nothing
        path = get_file_path(content_id)

        if not os.path.exists(path):
            continue # Exists neither on disk nor in the database - do nothing

        one_day = 24 * 60 * 60
        if time() - os.path.getctime(path) < one_day:
            log.debug("File %d not removed - created too recently" % content_id)
            continue # File created too recently - do nothing

        # File uploaded a while ago but not in the database - remove it
        log.debug("Deleting %s" % path)
        os.remove(path)
        count += 1

    log.info(
            "Removed %d from disk that where no longer referenced in the db"
            % count
            )


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


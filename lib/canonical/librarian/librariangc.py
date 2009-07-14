# Copyright 2004-2009 Canonical Ltd.  All rights reserved.
"""Librarian garbage collection routines"""

__metaclass__ = type

from datetime import datetime, timedelta
import errno
import sys
from time import time
import os

from zope.interface import implements

from canonical.config import config
from canonical.database.postgresql import quoteIdentifier
from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.utilities.looptuner import DBLoopTuner
from canonical.librarian.storage import _relFileLocation as relative_file_path
from canonical.librarian.storage import _sameFile
from canonical.database.postgresql import listReferences

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
            if config.instance_name == 'staging':
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


class UnreferencedLibraryFileContentPruner:
    """Delete unreferenced LibraryFileAliases.

    The LibraryFileContent records are left untouched for the code that
    knows how to delete them and the corresponding files on disk.

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
    implements(ITunableLoop)

    def __init__(self, con):
        self.con = con # Database connection to use
        self.total_deleted = 0 # Running total
        self.index = 1

        log.info("Deleting unreferenced LibraryFileAliases")

        cur = con.cursor()

        # Start with a list of all unexpired and recently accessed
        # content - we don't remove them even if they are unlinked. We
        # currently don't remove stuff until it has been expired for
        # more than one week, but we will change this if disk space
        # becomes short and it actually will make a noticeable
        # difference. Note that ReferencedLibraryFileContent will
        # contain duplicates - duplicates are unusual so we are better
        # off filtering them once at the end rather than when we load
        # the data into the temporary file.
        cur.execute("DROP TABLE IF EXISTS ReferencedLibraryFileContent")
        cur.execute("""
            SELECT LibraryFileAlias.content
            INTO TEMPORARY TABLE ReferencedLibraryFileContent
            FROM LibraryFileAlias
            WHERE
                expires >
                    CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - interval '1 week'
                OR last_accessed >
                    CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - interval '1 week'
                OR date_created >
                    CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - interval '1 week'
            """)
        con.commit()

        # Determine what columns link to LibraryFileAlias
        # references = [(table, column), ...]
        references = [
            tuple(ref[:2])
            for ref in listReferences(cur, 'libraryfilealias', 'id')
            if ref[0] != 'libraryfiledownloadcount'
            ]
        assert len(references) > 10, (
            'Database introspection returned nonsense')
        log.debug(
            "Found %d columns referencing LibraryFileAlias", len(references))

        # Find all relevant LibraryFileAlias references and fill in
        # ReferencedLibraryFileContent
        for table, column in references:
            log.debug("Getting references from %s.%s." % (table, column))
            cur.execute("""
                INSERT INTO ReferencedLibraryFileContent
                SELECT LibraryFileAlias.content
                FROM LibraryFileAlias, %(table)s
                WHERE LibraryFileAlias.id = %(table)s.%(column)s
                """ % {
                    'table': quoteIdentifier(table),
                    'column': quoteIdentifier(column)})
            con.commit()

        log.debug("Calculating expired unreferenced LibraryFileContent set.")
        cur.execute("DROP TABLE IF EXISTS UnreferencedLibraryFileContent")
        cur.execute("""
            CREATE TEMPORARY TABLE UnreferencedLibraryFileContent (
                id serial PRIMARY KEY,
                content integer UNIQUE)
            """)
        cur.execute("""
            INSERT INTO UnreferencedLibraryFileContent (content)
            SELECT id AS content FROM LibraryFileContent
            EXCEPT
            SELECT content FROM ReferencedLibraryFileContent
            """)
        cur.execute("DROP TABLE ReferencedLibraryFileContent")
        cur.execute(
            "SELECT COALESCE(max(id),0) FROM UnreferencedLibraryFileContent")
        self.max_id = cur.fetchone()[0]
        log.debug("%d unferenced LibraryFileContent to remove." % self.max_id)
        con.commit()

    def isDone(self):
        if self.index > self.max_id:
            log.info(
                "Deleted %d LibraryFileAlias records." % self.total_deleted)
            return True
        else:
            return False

    def __call__(self, chunksize):
        chunksize = int(chunksize)
        cur = self.con.cursor()
        cur.execute("""
            DELETE FROM LibraryFileAlias
            USING (
                SELECT content FROM UnreferencedLibraryFileContent
                WHERE id BETWEEN %s AND %s
                ) AS UnreferencedLibraryFileContent
            WHERE LibraryFileAlias.content
                = UnreferencedLibraryFileContent.content
            """, (self.index, self.index + chunksize - 1))
        deleted_rows = cur.rowcount
        self.total_deleted += deleted_rows
        log.debug("Deleted %d LibraryFileAlias records." % deleted_rows)
        self.con.commit()
        self.index += chunksize


def delete_unreferenced_aliases(con):
    "Run the UnreferencedLibraryFileContentPruner."
    loop_tuner = DBLoopTuner(
        UnreferencedLibraryFileContentPruner(con), 5, log=log)
    loop_tuner.run()


class UnreferencedContentPruner:
    """Delete LibraryFileContent entries and their disk files that are
    not referenced by any LibraryFileAlias entries.

    Note that a LibraryFileContent can only be accessed through a
    LibraryFileAlias, so all entries in this state are garbage no matter
    what their expires flag says.
    """
    implements(ITunableLoop)

    def __init__(self, con):
        self.con = con
        self.index = 1
        self.total_deleted = 0
        cur = con.cursor()
        cur.execute("DROP TABLE IF EXISTS UnreferencedLibraryFileContent")
        cur.execute("""
            CREATE TEMPORARY TABLE UnreferencedLibraryFileContent (
                id serial PRIMARY KEY,
                content integer UNIQUE)
            """)
        cur.execute("""
            INSERT INTO UnreferencedLibraryFileContent (content)
            SELECT DISTINCT LibraryFileContent.id
            FROM LibraryFileContent
            LEFT OUTER JOIN LibraryFileAlias
                ON LibraryFileContent.id = LibraryFileAlias.content
            WHERE LibraryFileAlias.content IS NULL
        """)
        cur.execute("""
            SELECT COALESCE(max(id), 0) FROM UnreferencedLibraryFileContent
            """)
        self.max_id = cur.fetchone()[0]
        log.debug("%d unreferenced LibraryFileContent rows to remove.")

    def isDone(self):
        if self.index > self.max_id:
            log.info("Deleted %d unreferenced files." % self.total_deleted)
            return True
        else:
            return False

    def __call__(self, chunksize):
        chunksize = int(chunksize)

        cur = self.con.cursor()

        # Delete unreferenced LibraryFileContent entries.
        cur.execute("""
            DELETE FROM LibraryFileContent
            USING (
                SELECT content FROM UnreferencedLibraryFileContent
                WHERE id BETWEEN %s AND %s) AS UnreferencedLibraryFileContent
            WHERE
                LibraryFileContent.id = UnreferencedLibraryFileContent.content
            """, (self.index, self.index + chunksize - 1))
        rows_deleted = cur.rowcount
        self.total_deleted += rows_deleted
        self.con.commit()

        # Remove files from disk. We do this outside the transaction,
        # as the garbage collector happily deals with files that exist
        # on disk but not in the DB.
        cur.execute("""
            SELECT content FROM UnreferencedLibraryFileContent
            WHERE id BETWEEN %s AND %s
            """, (self.index, self.index + chunksize - 1))
        for content_id in (row[0] for row in cur.fetchall()):
            # Remove the file from disk, if it hasn't already been
            path = get_file_path(content_id)
            try:
                os.unlink(path)
                log.debug("Deleted %s", path)
            except OSError, e:
                if e.errno != errno.ENOENT:
                    raise
                if config.librarian_server.upstream_host is None:
                    # It is normal to have files in the database that
                    # are not on disk if the Librarian has an upstream
                    # Librarian, such as on staging. Don't annoy the
                    # operator with noise in this case.
                    log.info("%s already deleted", path)

        self.index += chunksize


def delete_unreferenced_content(con):
    """Invoke UnreferencedContentPruner."""
    loop_tuner = DBLoopTuner(UnreferencedContentPruner(con), 5, log=log)
    loop_tuner.run()


class FlagExpiredFiles:
    """Flag files past their expiry date as 'deleted' in the database.

    Actual removal from disk is not performed here - that is deferred to
    delete_unwanted_files().
    """
    implements(ITunableLoop)

    def __init__(self, con):
        self.con = con
        self.index = 1
        self.total_flagged = 0
        cur = con.cursor()

        log.debug("Creating set of expired LibraryFileContent.")
        cur.execute("DROP TABLE IF EXISTS ExpiredLibraryFileContent")
        cur.execute("""
            CREATE TEMPORARY TABLE ExpiredLibraryFileContent
            (id serial PRIMARY KEY, content integer UNIQUE)
            """)
        cur.execute("""
            INSERT INTO ExpiredLibraryFileContent (content)
            SELECT id FROM LibraryFileContent WHERE deleted IS FALSE
            EXCEPT ALL
            SELECT DISTINCT content
            FROM LibraryFileAlias
            WHERE expires IS NULL
                OR expires >= CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
            """)
        cur.execute(
            "SELECT COALESCE(max(id),0) FROM ExpiredLibraryFileContent")
        self.max_id = cur.fetchone()[0]
        log.debug(
            "%d expired LibraryFileContent to flag for removal."
            % self.max_id)

    def isDone(self):
        if self.index > self.max_id:
            log.info(
                "Flagged %d expired files for removal."
                % self.total_flagged)
            return True
        else:
            return False

    def __call__(self, chunksize):
        chunksize = int(chunksize)
        cur = self.con.cursor()
        cur.execute("""
            UPDATE LibraryFileContent SET deleted=TRUE
            FROM (
                SELECT content FROM ExpiredLibraryFileContent
                WHERE id BETWEEN %s AND %s
                ) AS ExpiredLibraryFileContent
            WHERE LibraryFileContent.id = ExpiredLibraryFileContent.content
            """, (self.index, self.index + chunksize - 1))
        flagged_rows = cur.rowcount
        log.debug(
            "Flagged %d expired LibraryFileContent for removal."
            % flagged_rows)
        self.total_flagged += flagged_rows
        self.index += chunksize
        self.con.commit()


def flag_expired_files(connection):
    """Invoke FlagExpiredFiles."""
    loop_tuner = DBLoopTuner(FlagExpiredFiles(connection), 5, log=log)
    loop_tuner.run()


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

    # Calculate all stored LibraryFileContent ids that we want to keep.
    # Results are ordered so we don't have to suck them all in at once.
    cur.execute("""
        SELECT id FROM LibraryFileContent
        WHERE deleted IS FALSE OR datecreated
            > CURRENT_TIMESTAMP AT TIME ZONE 'UTC' - '1 day'::interval
        ORDER BY id
        """)

    def get_next_wanted_content_id():
        result = cur.fetchone()
        if result is None:
            return None
        else:
            return result[0]

    count = 0
    next_wanted_content_id = get_next_wanted_content_id()

    for content_id in range(1, max_id+1):
        while (next_wanted_content_id is not None
                and content_id > next_wanted_content_id):
            next_wanted_content_id = get_next_wanted_content_id()

        file_wanted = (
                next_wanted_content_id is not None
                and next_wanted_content_id == content_id)

        path = get_file_path(content_id)

        if file_wanted:
            if (config.librarian_server.upstream_host is None
                and not os.path.exists(path)):
                # It is normal to have files in the database that are
                # not on disk if the Librarian has an upstream
                # Librarian, such as on staging. Don't spam in this
                # case.
                log.error(
                    "LibraryFileContent %d exists in the db but not at %s"
                    % (content_id, path))

        else:
            try:
                one_day = 24 * 60 * 60
                if time() - os.path.getctime(path) < one_day:
                    log.debug(
                        "File %d not removed - created too recently"
                        % content_id)
                else:
                    # File uploaded a while ago but no longer wanted.
                    os.unlink(path)
                    log.debug("Deleted %s" % path)
                    count += 1
            except OSError, e:
                if e.errno != errno.ENOENT:
                    raise
                if config.librarian_server.upstream_host is None:
                    # It is normal to have files in the database that
                    # are not on disk if the Librarian has an upstream
                    # Librarian, such as on staging. Don't annoy the
                    # operator with noise in this case.
                    log.info("%s already deleted", path)

    log.info(
            "Deleted %d files from disk that where no longer referenced "
            "in the db" % count
            )


def get_file_path(content_id):
    """Return the physical file path to the matching LibraryFileContent id.
    """
    assert isinstance(content_id, (int, long)), 'Invalid content_id %r' % (
            content_id,
            )
    storage_root = config.librarian_server.root
    # Do a basic sanity check.
    if not os.path.isdir(os.path.join(storage_root, 'incoming')):
        raise RuntimeError(
                "Librarian file storage not found at %s" % storage_root
                )
    path = os.path.join(
            storage_root, relative_file_path(content_id)
            )
    return path


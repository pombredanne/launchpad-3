# (c) Canonical Software Ltd. 2004-2006, all rights reserved.
"""
Processes removals of packages that are scheduled for deletion.
"""

import datetime
import logging
import pytz
import os

from zope.security.proxy import removeSecurityProxy

from canonical.archivepublisher import ELIGIBLE_DOMINATION_STATES
from canonical.archivepublisher.config import LucilleConfigError
from canonical.archivepublisher.diskpool import DiskPool

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import sqlvalues

from canonical.launchpad.database.publishing import (
    SourcePackageFilePublishing, SecureSourcePackagePublishingHistory,
    BinaryPackageFilePublishing, SecureBinaryPackagePublishingHistory)
from canonical.launchpad.interfaces import (
    ArchivePurpose, ISecureSourcePackagePublishingHistory,
    ISecureBinaryPackagePublishingHistory, NotInPool)


def getDeathRow(archive, log, pool_root_override):
    """Return a Deathrow object for the archive supplied.

    :param archive: Use the publisher config for this archive to derive the
                    DeathRow object.
    :param log: Use this logger for script debug logging.
    :param pool_root_override: Use this pool root for the archive instead of
         the one provided by the publishing-configuration, it will be only
         used for PRIMARY archives.
    """
    log.debug("Grab Lucille config.")
    try:
        pubconf = archive.getPubConfig()
    except LucilleConfigError, info:
        log.error(info)
        raise

    pubconf = removeSecurityProxy(pubconf)

    if (pool_root_override is not None and
        archive.purpose == ArchivePurpose.PRIMARY):
        pool_root = pool_root_override
    else:
        pool_root = pubconf.poolroot

    log.debug("Preparing on-disk pool representation.")

    diskpool_log = logging.getLogger("DiskPool")
    # Set the diskpool's log level to INFO to suppress debug output
    diskpool_log.setLevel(20)

    dp = DiskPool(pool_root, pubconf.temproot, diskpool_log)

    log.debug("Preparing death row.")
    return DeathRow(archive, dp, log)


class DeathRow:
    """A Distribution Archive Removal Processor.

    DeathRow will remove archive files from disk if they are marked for
    removal in the publisher tables, and if they are no longer referenced
    by other packages.
    """
    def __init__(self, archive, diskpool, logger):
        self.archive = archive
        self.diskpool = diskpool
        self._removeFile = diskpool.removeFile
        self.logger = logger

    def reap(self, dry_run=False):
        """Reap packages that should be removed from the distribution.

        Looks through all packages that are in condemned states and
        have scheduleddeletiondate is in the past, try to remove their
        files from the archive pool (which may be impossible if they are
        used by other packages which are published), and mark them as
        removed."""
        if dry_run:
            # Don't actually remove the files if we are dry running
            def _mockRemoveFile(cn, sn, fn):
                self.logger.debug("(Not really!) removing %s %s/%s" %
                                  (cn, sn, fn))
                fullpath = self.diskpool.pathFor(cn, sn, fn)
                if not os.path.exists(fullpath):
                    raise NotInPool
                return os.lstat(fullpath).st_size
            self._removeFile = _mockRemoveFile

        source_files, binary_files = self._collectCondemned()
        records = self._tryRemovingFromDisk(source_files, binary_files)
        self._markPublicationRemoved(records)

    def _collectCondemned(self):
        source_files = SourcePackageFilePublishing.select("""
            publishingstatus IN %s AND
            sourcepackagefilepublishing.archive = %s AND
            SourcePackagePublishingHistory.id =
                 SourcePackageFilePublishing.sourcepackagepublishing AND
            SourcePackagePublishingHistory.dateremoved is NULL AND
            SourcePackagePublishingHistory.scheduleddeletiondate
                 is not NULL AND
            SourcePackagePublishingHistory.scheduleddeletiondate <= %s
            """ % sqlvalues(ELIGIBLE_DOMINATION_STATES, self.archive,
                            UTC_NOW),
            clauseTables=['SourcePackagePublishingHistory'],
            orderBy="id")

        self.logger.debug("%d Sources" % source_files.count())

        binary_files = BinaryPackageFilePublishing.select("""
            publishingstatus IN %s AND
            binarypackagefilepublishing.archive = %s AND
            BinaryPackagePublishingHistory.id =
                 BinaryPackageFilePublishing.binarypackagepublishing AND
            BinaryPackagePublishingHistory.dateremoved is NULL AND
            BinaryPackagePublishingHistory.scheduleddeletiondate
                 is not NULL AND
            BinaryPackagePublishingHistory.scheduleddeletiondate <= %s
            """ % sqlvalues(ELIGIBLE_DOMINATION_STATES, self.archive,
                            UTC_NOW),
            clauseTables=['BinaryPackagePublishingHistory'],
            orderBy="id")

        self.logger.debug("%d Binaries" % binary_files.count())

        return (source_files, binary_files)

    def canRemove(self, publication_class, file_md5):
        """Check if given MD5 can be removed from the archive pool.

        Check the archive reference-counter implemented in:
        `SecureSourcePackagePublishingHistory` or
        `SecureBinaryPackagePublishingHistory`.

        Only allow removal of unnecessary files.
        """
        clauses = []
        clauseTables = []

        if ISecureSourcePackagePublishingHistory.implementedBy(
            publication_class):
            clauses.append("""
                SecureSourcePackagePublishingHistory.archive = %s AND
                SecureSourcePackagePublishingHistory.dateremoved is NULL AND
                SecureSourcePackagePublishingHistory.sourcepackagerelease =
                    SourcePackageReleaseFile.sourcepackagerelease AND
                SourcePackageReleaseFile.libraryfile = LibraryFileAlias.id
            """ % sqlvalues(self.archive))
            clauseTables.append('SourcePackageReleaseFile')
        elif ISecureBinaryPackagePublishingHistory.implementedBy(
            publication_class):
            clauses.append("""
                SecureBinaryPackagePublishingHistory.archive = %s AND
                SecureBinaryPackagePublishingHistory.dateremoved is NULL AND
                SecureBinaryPackagePublishingHistory.binarypackagerelease =
                    BinaryPackageFile.binarypackagerelease AND
                BinaryPackageFile.libraryfile = LibraryFileAlias.id
            """ % sqlvalues(self.archive))
            clauseTables.append('BinaryPackageFile')
        else:
            raise AssertionError("%r is not supported." % publication_class)

        clauses.append("""
           LibraryFileAlias.content = LibraryFileContent.id AND
           LibraryFileContent.md5 = %s
        """ % sqlvalues(file_md5))
        clauseTables.extend(
            ['LibraryFileAlias', 'LibraryFileContent'])

        all_publications = publication_class.select(
            " AND ".join(clauses), clauseTables=clauseTables)

        right_now = datetime.datetime.now(pytz.timezone('UTC'))
        for pub in all_publications:
            # Deny removal if any reference is still active.
            if pub.status not in ELIGIBLE_DOMINATION_STATES:
                return False
            # Deny removal if any reference wasn't dominated yet.
            if pub.scheduleddeletiondate is None:
                return False
            # Deny removal if any reference is still in 'quarantine'.
            # See PubConfig.pendingremovalduration value.
            if pub.scheduleddeletiondate > right_now:
                return False

        return True

    def _tryRemovingFromDisk(self, condemned_source_files,
                             condemned_binary_files):
        """Take the list of publishing records provided and unpublish them.

        You should only pass in entries you want to be unpublished because
        this will result in the files being removed if they're not otherwise
        in use.
        """
        bytes = 0
        condemned_files = set()
        condemned_records = set()
        considered_md5s = set()
        details = {}

        content_files = (
            (SecureSourcePackagePublishingHistory, condemned_source_files),
            (SecureBinaryPackagePublishingHistory, condemned_binary_files),)

        for publication_class, pub_files in content_files:
            for pub_file in pub_files:
                file_md5 = pub_file.libraryfilealias.content.md5
                # Check if the LibraryFileAlias in question was already
                # verified. If it was, continue.
                if file_md5 in considered_md5s:
                    continue
                considered_md5s.add(file_md5)

                filename = pub_file.libraryfilealiasfilename
                # Check if the removal is allowed, if not continue.
                if not self.canRemove(publication_class, file_md5):
                    continue

                # Update local containers, in preparation to file removal.
                pub_file_details = (
                    pub_file.libraryfilealiasfilename,
                    pub_file.sourcepackagename,
                    pub_file.componentname,
                    )
                file_path = self.diskpool.pathFor(*pub_file_details)
                details.setdefault(file_path, pub_file_details)
                condemned_files.add(file_path)
                condemned_records.add(pub_file.publishing_record)

        self.logger.info(
            "Removing %s files marked for reaping" % len(condemned_files))

        for condemned_file in sorted(condemned_files, reverse=True):
            file_name, source_name, component_name = details[condemned_file]
            try:
                bytes += self._removeFile(
                    component_name, source_name, file_name)
            except NotInPool:
                # It's safe for us to let this slide because it means that
                # the file is already gone.
                self.logger.debug(
                    "File to remove %s %s/%s is not in pool, skipping" %
                    (component_name, source_name, file_name))
            except:
                self.logger.exception(
                    "Removing file %s %s/%s generated exception, continuing" %
                    (component_name, source_name, file_name))

        self.logger.info("Total bytes freed: %s" % bytes)

        return condemned_records

    def _markPublicationRemoved(self, condemned_records):
        # Now that the os.remove() calls have been made, simply let every
        # now out-of-date record be marked as removed.
        self.logger.debug("Marking %s condemned packages as removed." %
                          len(condemned_records))
        for record in condemned_records:
            record.dateremoved = UTC_NOW


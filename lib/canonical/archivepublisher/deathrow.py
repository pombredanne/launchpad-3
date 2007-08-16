# (c) Canonical Software Ltd. 2004-2006, all rights reserved.
"""
Processes removals of packages that are scheduled for deletion.
"""

import datetime
import logging
import pytz
import os

from canonical.archivepublisher.config import LucilleConfigError
from canonical.archivepublisher.diskpool import DiskPool

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import sqlvalues

from canonical.launchpad.database.publishing import (
    SourcePackageFilePublishing, BinaryPackageFilePublishing)
from canonical.launchpad.interfaces import NotInPool
from canonical.lp.dbschema import PackagePublishingStatus


def getDeathRow(archive, log, pool_root_override):
    """Return a Deathrow object for the archive supplied.

    :param archive: Use the publisher config for this archive to derive the
                    DeathRow object.
    :param log: Use this logger for script debug logging.
    :param pool_root_override: Use this pool root for the archive instead of
                               its publisher configured value.
    """
    log.debug("Grab Lucille config.")
    try:
        pubconf = archive.getPubConfig()
    except LucilleConfigError, info:
        log.error(info)
        raise

    if pool_root_override is not None:
        pool_root = pool_root_override
    else:
        pool_root = pubconf.poolroot

    log.debug("Preparing on-disk pool representation.")
    dp = DiskPool(pool_root, pubconf.temproot,
        logging.getLogger("DiskPool"))
    # Set the diskpool's log level to INFO to suppress debug output
    dp.logger.setLevel(20)

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
        self.distribution = archive.distribution
        self.diskpool = diskpool
        self._removeFile = diskpool.removeFile
        self.logger = logger

    def reap(self, dry_run=False):
        """Reap packages that should be removed from the distribution.

        Looks through all packages that are in PENDINGREMOVAL status and
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
            publishingstatus = %s AND
            distribution = %s AND
            sourcepackagefilepublishing.archive = %s AND
            SourcePackagePublishingHistory.id =
                 SourcePackageFilePublishing.sourcepackagepublishing AND
            SourcePackagePublishingHistory.scheduleddeletiondate <= %s
            """ % sqlvalues(PackagePublishingStatus.PENDINGREMOVAL,
                            self.distribution,
                            self.archive,
                            UTC_NOW),
            clauseTables=['SourcePackagePublishingHistory'],
            orderBy="id")

        binary_files = BinaryPackageFilePublishing.select("""
            publishingstatus = %s AND
            distribution = %s AND
            binarypackagefilepublishing.archive = %s AND
            BinaryPackagePublishingHistory.id =
                 BinaryPackageFilePublishing.binarypackagepublishing AND
            BinaryPackagePublishingHistory.scheduleddeletiondate <= %s
            """ % sqlvalues(PackagePublishingStatus.PENDINGREMOVAL,
                            self.distribution,
                            self.archive,
                            UTC_NOW),
            clauseTables=['BinaryPackagePublishingHistory'],
            orderBy="id")
        return (source_files, binary_files)

    def canRemove(self, publication_class, filename):
        """Whether or not a filename can be remove of the archive pool.

        Check the archive reference-counter implemented in:
        `SourcePackageFilePublishing` or `BinaryPackageFilePublishing`.

        Only allow removal of unnecessary files.
        """
        # 'prejoin'ing {S,B}PPH would help here if we face performance
        # problems, but we can not do it dynamically due to the hack
        # performed by IArchiveFilePublishing.publishing_record which
        # 'magically' decided what is the respective publishing record
        # needs to be retrieved. Something in direction of:
        # "default_prejoins = 'SPPH' or 'BPPH'" would work very
        # well for Source/BinaryPackageFilePublishing classes in this case.
        # However we are still able to decide what to 'prejoin' here, in the
        # callsite by testing what is the interface implemented by the
        # publication_class.
        all_publications = publication_class.select("""
           libraryfilealiasfilename = %s AND
           distribution = %s AND
           archive = %s
        """ % sqlvalues(filename, self.distribution,
                        self.distribution.main_archive))

        right_now = datetime.datetime.now(pytz.timezone('UTC'))

        for file_pub in all_publications:
            # Deny removal if any reference is still active.
            if (file_pub.publishingstatus !=
                PackagePublishingStatus.PENDINGREMOVAL):
                return False
            # Deny removal if any reference is still in 'quarantine'.
            # See PubConfig.pendingremovalduration value.
            if (file_pub.publishing_record.scheduleddeletiondate >
                right_now):
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
        details = {}

        content_files = (
            (SourcePackageFilePublishing, condemned_source_files),
            (BinaryPackageFilePublishing, condemned_binary_files),)

        for publication_class, pub_files in content_files:
            for pub_file in pub_files:
                # Check if the removal is allowed, if not continue.
                if not self.canRemove(
                    publication_class, pub_file.libraryfilealiasfilename):
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

        for condemened_file in sorted(condemned_files, reverse=True):
            file_name, source_name, component_name = details[condemened_file]
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
            record.status = PackagePublishingStatus.REMOVED
            record.dateremoved = UTC_NOW


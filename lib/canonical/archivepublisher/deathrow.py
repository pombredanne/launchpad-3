# (c) Canonical Software Ltd. 2004-2006, all rights reserved.
"""
Processes removals of packages that are scheduled for deletion.
"""

import os

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import sqlvalues

from canonical.lp.dbschema import PackagePublishingStatus

from canonical.launchpad.interfaces import NotInPool

from canonical.launchpad.database.publishing import (
    SourcePackageFilePublishing, BinaryPackageFilePublishing)


class DeathRow:
    """A Distribution Archive Removal Processor."""
    def __init__(self, distribution, diskpool, logger):
        self.distribution = distribution
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
                            self.distribution, self.distribution.main_archive,
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
                            self.distribution, self.distribution.main_archive,
                            UTC_NOW),
            clauseTables=['BinaryPackagePublishingHistory'],
            orderBy="id")
        return (source_files, binary_files)

    def _tryRemovingFromDisk(self, condemned_source_files,
                             condemned_binary_files):
        """Take the list of publishing records provided and unpublish them.

        You should only pass in entries you want to be unpublished because
        this will result in the files being removed if they're not otherwise
        in use.
        """

        def updateDetails(p, details):
            fn = p.libraryfilealiasfilename
            sn = p.sourcepackagename
            cn = p.componentname
            filename = self.diskpool.pathFor(cn, sn, fn)
            details.setdefault(filename, [cn, sn, fn])
            return filename

        bytes = 0
        live_files = set()
        condemned_files = set()
        condemned_records = set()
        details = {}

        live_source_files = SourcePackageFilePublishing.select(
            """
            distribution = %s AND
            SourcePackagePublishingHistory.archive = %s AND
            publishingstatus != %s AND
            SourcePackagePublishingHistory.id =
            SourcePackageFilePublishing.sourcepackagepublishing AND
            (publishingstatus != %s OR
             SourcePackagePublishingHistory.scheduleddeletiondate > %s)
            """ % sqlvalues(self.distribution,
                            self.distribution.main_archive,
                            PackagePublishingStatus.REMOVED,
                            PackagePublishingStatus.PENDINGREMOVAL,
                            UTC_NOW),
            clauseTables = ["SourcePackagePublishingHistory"],
            orderBy="id")
        live_binary_files = BinaryPackageFilePublishing.select(
            """
            distribution = %s AND
            BinaryPackagePublishingHistory.archive = %s AND
            publishingstatus != %s AND
            BinaryPackagePublishingHistory.id =
            BinaryPackageFilePublishing.binarypackagepublishing AND
            (publishingstatus != %s OR
             BinaryPackagePublishingHistory.scheduleddeletiondate > %s)
             """ % sqlvalues(self.distribution,
                             self.distribution.main_archive,
                             PackagePublishingStatus.REMOVED,
                             PackagePublishingStatus.PENDINGREMOVAL,
                             UTC_NOW),
            clauseTables = ["BinaryPackagePublishingHistory"],
            orderBy="id")

        for p in live_source_files:
            filename = updateDetails(p, details)
            live_files.add(filename)
        for p in live_binary_files:
            filename = updateDetails(p, details)
            live_files.add(filename)
        for p in condemned_source_files:
            filename = updateDetails(p, details)
            condemned_files.add(filename)
            condemned_records.add(p.sourcepackagepublishing)
        for p in condemned_binary_files:
            filename = updateDetails(p, details)
            condemned_files.add(filename)
            condemned_records.add(p.binarypackagepublishing)

        remove_files = condemned_files - live_files
        self.logger.info("Removing %s files marked for reaping" %
                         len(remove_files))
        for f in remove_files:
            try:
                cn, sn, fn = details[f]
                bytes += self._removeFile(cn, sn, fn)
            except NotInPool:
                # It's safe for us to let this slide because it means that
                # the file is already gone.
                self.logger.debug("File to remove %s %s/%s is not in pool, "
                                  "skipping" % (cn, sn, fn))
            except:
                self.logger.exception("Removing file %s %s/%s generated "
                                      "exception, continuing" % (cn, sn, fn))

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


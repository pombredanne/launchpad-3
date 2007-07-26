# (c) Canonical Software Ltd. 2004-2006, all rights reserved.
"""
Processes removals of packages that are scheduled for deletion.
"""

import datetime
import pytz
import os

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import sqlvalues

from canonical.launchpad.database.publishing import (
    SourcePackageFilePublishing, BinaryPackageFilePublishing)
from canonical.launchpad.interfaces import NotInPool
from canonical.lp.dbschema import PackagePublishingStatus


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
            sourcepackagefilepublishing.archive IN %s AND
            SourcePackagePublishingHistory.id =
                 SourcePackageFilePublishing.sourcepackagepublishing AND
            SourcePackagePublishingHistory.scheduleddeletiondate <= %s
            """ % sqlvalues(PackagePublishingStatus.PENDINGREMOVAL,
                            self.distribution, 
                            [archive.id for archive in 
                                self.distribution.all_distro_archives],
                            UTC_NOW),
            clauseTables=['SourcePackagePublishingHistory'],
            orderBy="id")

        binary_files = BinaryPackageFilePublishing.select("""
            publishingstatus = %s AND
            distribution = %s AND
            binarypackagefilepublishing.archive IN %s AND
            BinaryPackagePublishingHistory.id =
                 BinaryPackageFilePublishing.binarypackagepublishing AND
            BinaryPackagePublishingHistory.scheduleddeletiondate <= %s
            """ % sqlvalues(PackagePublishingStatus.PENDINGREMOVAL,
                            self.distribution, 
                            [archive.id for archive in
                                self.distribution.all_distro_archives],
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

        def updateDetails(p):
            fn = p.libraryfilealiasfilename
            sn = p.sourcepackagename
            cn = p.componentname
            filename = self.diskpool.pathFor(cn, sn, fn)
            details.setdefault(filename, [cn, sn, fn])
            condemned_files.add(filename)
            condemned_records.add(p.publishing_record)

        def canRemove(content, filename):
            # XXX cprov 20070723: 'prejoin'ing {S,B}PPH would help, but we can
            # not do it dynamically due to the hack performed by
            # IArchiveFilePublishing.publishing_record. Although, something in
            # direction of default_prejoins = 'SPPH' or 'BPPH' would work very
            # well for Source/BinaryPackageFilePublishing class.
            all_publications = content.select("""
            libraryfilealiasfilename = %s AND distribution = %s AND
            archive = %s""" % sqlvalues(
                filename, self.distribution, 
                [archive.id for archive in 
                    self.distribution.all_distro_archives]))
            for p in all_publications:
                if p.publishingstatus != PackagePublishingStatus.PENDINGREMOVAL:
                    return False
                if p.publishing_record.scheduleddeletiondate > right_now:
                    return False
            return True

        bytes = 0
        condemned_files = set()
        condemned_records = set()
        details = {}
        right_now = datetime.datetime.now(pytz.timezone('UTC'))

        content_files = (
            (SourcePackageFilePublishing, condemned_source_files),
            (BinaryPackageFilePublishing, condemned_binary_files),)

        for content, pub_files in content_files:
            for pub in pub_files:
                filename = pub.libraryfilealiasfilename
                if canRemove(content, filename):
                    updateDetails(pub)

        self.logger.info(
            "Removing %s files marked for reaping" % len(condemned_files))

        for f in condemned_files:
            try:
                cn, sn, fn = details[f]
                bytes += self._removeFile(cn, sn, fn)
            except NotInPool:
                # It's safe for us to let this slide because it means that
                # the file is already gone.
                self.logger.debug(
                    "File to remove %s %s/%s is not in pool, skipping" %
                    (cn, sn, fn))
            except:
                self.logger.exception(
                    "Removing file %s %s/%s generated exception, continuing" %
                    (cn, sn, fn))

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


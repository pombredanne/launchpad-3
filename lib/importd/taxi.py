################################################################################
#
#  Copyright (c) 2004 Canonical Ltd.
#  Authors: Rob Weir <rob.weir@canonical.com>
#           David Allouche <david@allouche.net>
#  
#  DO NOT ALTER THE NEXT LINE
#  arch-tag: 9ecc92f8-94d9-4639-a3c8-a29385d9fe71
# 
################################################################################

import time
import pybaz as arch

from canonical.arch import broker


class Taxi(object):
    """Import an archive into Launchpad."""

    def __init__(self, job):
        self.txnManager = None
        self.job = job
        self.archive_manager = job.makeArchiveManager()

    def _insertVersion(self, version, db_archive):
        """Create a version and its namespace containers in the database.

        :type version: `arch.Version`
        :param version: version to create in the database.
        :type db_archive: `canonical.arch.broker.Archive`
        :param db_archive: database archive to create the version into.
        """
        parser = arch.NameParser(version.fullname)
        C = parser.get_category()
        if db_archive[C].exists():
            db_category = db_archive[C]
        else:
            db_category = db_archive.create_category(C)
        B = parser.get_branch()
        if db_category[B].exists():
            db_branch = db_category[B]
        else:
            db_branch = db_category.create_branch(B)
        V = parser.get_version()
        if db_branch[V].exists():
            return db_branch[V]
        else:
            return db_branch.create_version(V)

    def _insertRevision(self, revision, version):
        r = arch.NameParser(revision.fullname).get_patchlevel()
        if not version[r].exists():
            return (version.create_revision(r), False)
        else:
            return (version[r], True)

    def importVersion(self):
        """Import a version."""
        archive_manager = self.archive_manager
        version = archive_manager.version

        self.txnManager.begin()
        db_archive = self.dbArchive(version.archive)
        db_version = self._insertVersion(version, db_archive)
        branch = db_version._sqlobject_branch
        branch.productID = self.job.product_id
        if not branch.description:
            branch.description = self.job.description
        if not branch.title:
            branch.title = str(version)
        mirror_location = archive_manager._mirror()
        db_mirror = self.dbMirror(db_archive, mirror_location.url)
        self.txnManager.commit()

        old_revisions, new_revisions = archive_manager.compareMasterToMirror()
        for revision in new_revisions:
            self.logger.warning("Copying new revision %s", revision)
            archive_manager.mirrorRevision(revision)
            self.txnManager.begin()
            self.doRevision(revision, db_version, db_archive)
            self.txnManager.commit()
        self.logger.warning("Refreshing %d revisions." % len(old_revisions))
        self.txnManager.begin()
        for revision in old_revisions:
            self.logger.warning("Refreshing revision %s", revision)
            self.doRevision(revision, db_version, db_archive)
        self.txnManager.commit()
        if len(old_revisions) != 0:
            self.logger.warning("Refreshed revisions up to %s" %
                                (old_revisions[-1].patchlevel,))

    def dbArchive(self, archive):
        archives = broker.Archives()
        db_archive = archives[archive.name]
        if db_archive.exists():
            return archives[archive.name]
        else:
            return archives.create(archive.name)

    def dbMirror(self, db_archive, mirror_url):
        num_mirrors = len(db_archive.location.getMirrorTargetLocations())
        self.logger.warning("has %d registered mirrors", num_mirrors)
        # FIXME: handle multiple mirrors -- David Allouche 2005-02-08
        if num_mirrors == 0:
            db_archive.location.createMirrorTargetLocation(mirror_url)

        all_mirrors = db_archive.location.getMirrorTargetLocations()
        # FIXME: handle multiple mirrors -- David Allouche 2005-02-08
        assert len(all_mirrors) == 1
        # XXX should "mirror" be ever different from "to"?
        # If not, this code can be removed after fixing uses of self.mirror
        # -- David Allouche 2005-02-08
        return all_mirrors[0]

    def doRevision(self, revision, db_version, db_archive):
        db_revision, didExist = self._insertRevision(revision, db_version)
        if not didExist:
            self.logger.info("importing %s", revision.fullname)
            db_revision.set_patchlog(arch.Patchlog(revision))
        else:
            self.logger.info("skipping %s", revision.fullname)

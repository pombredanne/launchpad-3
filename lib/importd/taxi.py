################################################################################
#
#  Written by Rob Weir <rob.weir@canonical.com>
#  Copyright (c) 2004 Canonical Ltd.
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

    def __init__(self):
        self.txnManager = None
        self._hasBeenRun = False

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

    def _runOnlyOnce(self):
        """Use in methods that ``consume'' the Taxi.

        This method can be run only once without causing a RuntimeError.
        """
        if self._hasBeenRun:
            raise RuntimeError("Taxi cannot be run twice on the same instance."
                               " Please create a new instance.")
        self._hasBeenRun = True

    # FIXME: this and importArchive should be replaced with a import
    # method which takes a limit parameter and uses magic to decide
    # what to import.

    # XXX This FIXME does not make sense to me. -- David Allouche 2005-02-07

    def importVersion(self, version, to, product_id, title, description):
        """Import a version.

        :param version: official name of the version to mirror
        :type version: `arch.Version`
        :param to: location of the target mirror.
        :type to: str
        :param product_id: primary key of the product for this branch.
        :type product_id: int
        :param title: title of the branch in the database.
        :type title: str
        :param description: description of the branch in the database.
        :type description: str
        """
        self._runOnlyOnce()

        archives = broker.Archives()
        archive = archives[version.archive.name]
        if archive.exists():
            db_archive = archives[archive.name]
        else:
            db_archive = archives.create(archive.name)

        num_mirrors = len(archive.location.getMirrorTargetLocations())
        self.logger.warning("has %d registered mirrors", num_mirrors)
        # FIXME: handle multiple mirrors -- David Allouche 2005-02-08
        if num_mirrors == 0:
            archive.location.createMirrorTargetLocation(to)

        all_mirrors = archive.location.getMirrorTargetLocations()
        # FIXME: handle multiple mirrors -- David Allouche 2005-02-08
        assert len(all_mirrors) == 1
        # XXX should "mirror" be ever different from "to"?
        # If not, this code can be removed after fixing uses of self.mirror
        # -- David Allouche 2005-02-08
        mirror = all_mirrors[0]
        self.mirror = mirror # self.mirror is a ugly hack, should be fixed

        db_version = self._insertVersion(version, db_archive)
        db_version._sqlobject_branch.productID = product_id
        if not db_version._sqlobject_branch.description:
            db_version._sqlobject_branch.description = description
        if not db_version._sqlobject_branch.title:
            db_version._sqlobject_branch.title = title
        # XXX should we really commit here? -- David Allouche 2005-02-08
        self.txnManager.commit()

        # iterate over the new ones (start on the lowest one missing
        # from the destination archive).
        mirror_archive = self.findArchiveByLocation(mirror.url)
        mirror_ver = self.mirrorVersion(mirror_archive, version)
        if mirror_ver.exists():
            last_mirror_level = mirror_ver.latest_revision().patchlevel
            if last_mirror_level == "base-0":
                highrev = 0
            elif last_mirror_level.startswith("patch-"):
                highrev = int(last_mirror_level[len("patch-"):])
            else:
                raise RuntimeError("Can't handle patchlevel %r."
                                   % last_mirror_level)
            all_revisions = list(version.iter_revisions())
            old_revisions = all_revisions[:highrev + 1]
            new_revisions = all_revisions[highrev + 1:]
        else:
            old_revisions = []
            new_revisions = list(version.iter_revisions())
        for revision in new_revisions:
            self.logger.warning("Copying new revision %s", revision)
            self.doRevision(revision, db_version, db_archive)
            self.txnManager.commit()
        self.logger.warning("Refreshing %d revisions." % len(old_revisions))
        for revision in old_revisions:
            self.logger.warning("Refreshing revision %s", revision)
            self.doRevision(revision, db_version, db_archive, do_mirror=False)
        self.txnManager.commit()
        if len(old_revisions) != 0:
            self.logger.warning("Refreshed revisions up to %s" %
                                (old_revisions[-1].patchlevel,))


    def versionOnMirror(self, version):
        """return the -MIRROR version of version."""
        return arch.Version(self.findArchiveByLocation(self.mirror.url).name + "/" + version.nonarch)

    def revisionOnMirror(self, revision):
        """return the -MIRROR version of revision."""
        return arch.Revision(self.findArchiveByLocation(self.mirror.url).name + "/" + revision.nonarch)

    def mirrorVersion(self, mirror_archive, version):
        '''return the Version for the mirror we are targeting'''
        return arch.Version(mirror_archive.name + "/" + version.nonarch)

    def doRevision(self, revision, db_version, db_archive, do_mirror=True):
        if do_mirror:
            db_archive.mirror_revision(revision)
        db_revision, didExist = self._insertRevision(revision, db_version)
        if not didExist:
            self.logger.info("importing %s", revision.fullname)
            db_revision.set_patchlog(arch.Patchlog(revision))
            db_revision.clone_files(revision.iter_files())
        else:
            self.logger.info("skipping %s", revision.fullname)

    def findArchiveByLocation(self, location):
        """Find the registered name of an archive given its url.

        :param location: archive location, as found in archarchivelocation.url
            in the Launchpad database.
        :return: logical name of this according to ~/.arch-params.
        """
        matches = [A for A in arch.iter_archives() if A.location == location]
        if __debug__:
            if len(matches) != 1:
                msg = "Expected exactly one mirror for location %r, but got %r"
                raise AssertionError(msg % (location, matches))
        return matches[0]

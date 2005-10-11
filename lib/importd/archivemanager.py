# Copyright (c) 2005 Canonical Limited
# Licence to be determined
# Author: David Allouche <david@allouche.net>

import os
import shutil

import pybaz as arch

__all__ = [
    'ArchiveManager',
    'RevisionLibraryPresentError',
    'MirrorMoreUpToDateError',
    ]


class RevisionLibraryPresentError(Exception):
    """Raised by rollbackToMirror when a revision library is configured."""

    def __init__(self):
        Exception.__init__(
            self, "Revision library present, changing history is unsafe.")


class MirrorMoreUpToDateError(Exception):
    """Raised by rollbackToMirror if mirror is more up to date than master.
    """
    def __init__(self, mirror, version):
        Exception.__init__(
            self, "Mirror is more up to date than master: %s/%s"
            % (mirror.url, version.nonarch))


class MirrorButNoMasterError(Exception):
    """Raised by rollbackToMirror if mirror has the branch but master does not.
    """
    def __init__(self, mirror, version):
        Exception.__init__(
            self, "Branch present in mirror but not in master: %s/%s"
            % (mirror.url, version.nonarch))

class NukeMirroredMasterError(Exception):
    """Raised by nukeMaster if the mirror branch is not empty."""

    def __init__(self, mirror, version):
        Exception.__init__(
            self, "Tried to nuke master, but mirror is not empty: %s/%s"
            % (mirror.url, version.nonarch))


class ArchiveManager(object):

    def __init__(self, job):
        self.archive = arch.Archive(job.archivename)
        self.version = arch.Version(job.bazFullPackageVersion())
        self.master_dir = os.path.join(job.slave_home, 'archives')
        self.mirror_dir = job.archive_mirror_dir
        # master and mirror locations are cached to leverage the memoisation in
        # ArchiveLocation.archive.
        master_url = os.path.join(self.master_dir, self.archive.name)
        self.__master = arch.ArchiveLocation(master_url)
        mirror_url = os.path.join(self.mirror_dir, self.archive.name)
        self.__mirror = arch.ArchiveLocation(mirror_url)

    def createMaster(self):
        if not self._master().is_registered():
            params = arch.ArchiveLocationParams()
            params.signed = True
            self._master().create_master(self.archive, params)

    def _master(self):
        return self.__master

    def createMirror(self):
        if not self._mirror().is_registered():
            params = arch.ArchiveLocationParams()
            params.signed = True
            params.listing = True
            self._mirror().create_mirror(self.archive, params)

    def _mirror(self):
        return self.__mirror

    def nukeMaster(self):
        """Remove the master branch.

        Fail with RuntimeError if the mirror branch is not empty.
        """
        if not self.mirrorIsEmpty():
            raise NukeMirroredMasterError(self._mirror(), self.version)
        master = self._master()
        branch_url = self._versionUrl(master)
        if os.path.exists(branch_url):
            shutil.rmtree(branch_url)

    def rollbackToMirror(self):
        """Removes revisions in master that are not present in mirror.
        """
        if list(arch.iter_revision_libraries()):
            raise RevisionLibraryPresentError()
        exists_on_master = self._versionExistsInLocation(self._master())
        exists_on_mirror = self._versionExistsInLocation(self._mirror())
        if not exists_on_master and not exists_on_mirror:
            return
        if exists_on_master and not exists_on_mirror:
            shutil.rmtree(self._versionUrl(self._master()))
            return
        if not exists_on_master and exists_on_mirror:
            raise MirrorButNoMasterError(self._mirror(), self.version)
        mirror_levels = self._locationPatchlevels(self._mirror())
        master_levels = self._locationPatchlevels(self._master())
        if len(mirror_levels) > len(master_levels):
            raise MirrorMoreUpToDateError(self._mirror(), self.version)
        if mirror_levels != []:
            os.rename(self._masterLockUrl(master_levels[-1]),
                      self._masterLockUrl(mirror_levels[-1]))
        reverse_master_levels = list(master_levels)
        reverse_master_levels.reverse()
        for level in reverse_master_levels:
            if level in mirror_levels:
                break
            shutil.rmtree(self._revisionUrl(self._master(), level))

    def _versionExistsInLocation(self, location):
        versions = self.archive.iter_location_versions(location)
        return self.version in versions

    def _locationRevisions(self, location):
        return list(self.version.iter_location_revisions(location))

    def _locationPatchlevels(self, location):
        return [revision.patchlevel for revision
                in self._locationRevisions(location)]

    def _versionUrl(self, location):
        return "/".join((location.url, self.version.nonarch))

    def _revisionUrl(self, location, level):
        return "/".join((self._versionUrl(location), level))

    def _masterLockUrl(self, level):
        return "/".join((self._revisionUrl(self._master(), level),
                         '++revision-lock'))

    def compareMasterToMirror(self):
        """Tell which revisions in the master are mirrored and which are new.

        :return: Two lists, the first is mirrored (old) revisions, the second
            is unmirorrered (new) revisions.
        """
        master = self._master()
        mirror = self._mirror()
        if self._versionExistsInLocation(mirror):
            mirror_levels = self._locationPatchlevels(mirror)
            last_mirror_level = mirror_levels[-1]
            if last_mirror_level == "base-0":
                highrev = 0
            elif last_mirror_level.startswith("patch-"):
                highrev = int(last_mirror_level[len("patch-"):])
            else:
                raise RuntimeError("Can't handle patchlevel %r."
                                   % last_mirror_level)
            all_revisions = self._locationRevisions(master)
            old_revisions = all_revisions[:highrev + 1]
            new_revisions = all_revisions[highrev + 1:]
        elif self._versionExistsInLocation(master):
            old_revisions = []
            new_revisions = self._locationRevisions(master)
        else:
            old_revisions = []
            new_revisions = []
        return old_revisions, new_revisions

    def mirrorRevision(self, revision):
        mirrorer = self._master().make_mirrorer(self._mirror())
        mirrorer.mirror(revision)

    def mirrorIsEmpty(self):
        """Is the mirror empty or non-existent?

        :rtype: bool
        """
        mirror = self._mirror()
        if not mirror.is_registered():
            return True
        elif not self._versionExistsInLocation(mirror):
            return True
        elif self._locationPatchlevels(mirror) == []:
            return True
        else:
            return False


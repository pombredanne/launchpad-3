# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The processing of dist-upgrader tarballs."""

__metaclass__ = type

__all__ = ['process_dist_upgrader']

import os

from lp.archivepublisher.customupload import (
    CustomUpload,
    CustomUploadError,
    )
from lp.archivepublisher.debversion import (
    BadUpstreamError,
    Version as make_version,
    )


class DistUpgraderAlreadyExists(CustomUploadError):
    """A build for this type, version already exists."""
    def __init__(self, arch, version):
        message = ('dist-upgrader build %s for architecture %s already exists'%
                   (arch, version))
        CustomUploadError.__init__(self, message)


class DistUpgraderBadVersion(CustomUploadError):
    def __init__(self, tarfile_path, exc):
        message = "bad version found in '%s': %s" % (tarfile_path, str(exc))
        CustomUploadError.__init__(self, message)


class DistUpgraderUpload(CustomUpload):
    """Dist Upgrader custom upload processor.

    Dist-Upgrader is a tarball containing files for performing automatic
    distroseries upgrades, driven by architecture.

    The tarball should be name as:

      <NAME>_<VERSION>_<ARCH>.tar.gz

    where:

     * NAME: can be anything reasonable like 'dist-upgrader', it's not used;
     * VERSION: debian-like version token;
     * ARCH: debian-like architecture tag.

    and should contain:

     * ReleaseAnnouncement text file;
     * <distroseries>.tar.gz file.

    Dist-Upgrader versions are published under:

    <ARCHIVE>/dists/<SUITE>/main/dist-upgrader-<ARCH>/<VERSION>/

    A 'current' symbolic link points to the most recent version.
    """
    def __init__(self, archive_root, tarfile_path, distroseries):
        CustomUpload.__init__(self, archive_root, tarfile_path, distroseries)

        tarfile_base = os.path.basename(tarfile_path)
        name, self.version, arch = tarfile_base.split('_')
        arch = arch.split('.')[0]

        self.targetdir = os.path.join(archive_root, 'dists', distroseries,
                                      'main', 'dist-upgrader-%s' % arch)

        # Make sure the target version doesn't already exist. If it does, raise
        # DistUpgraderAlreadyExists.
        if os.path.exists(os.path.join(self.targetdir, self.version)):
            raise DistUpgraderAlreadyExists(arch, self.version)

    def shouldInstall(self, filename):
        """ Install files from a dist-upgrader tarball.

        It raises DistUpgraderBadVersion if if finds a directory name that
        could not be treated as a valid Debian version.

        It returns False for extracted contents of a directory named
        'current' (since it would obviously conflict with the symbolic
        link in the archive).

        Return True for contents of 'versionable' directories.
        """
        # Only the first path part (directory name) must be *versionable*
        # and we may allow subdirectories.
        directory_name = filename.split(os.path.sep)[0]
        try:
            version = make_version(directory_name)
        except BadUpstreamError, exc:
            raise DistUpgraderBadVersion(self.tarfile_path, exc)
        return version and not filename.startswith('current')


def process_dist_upgrader(archive_root, tarfile_path, distroseries):
    """Process a raw-dist-upgrader tarfile.

    Unpacking it into the given archive for the given distroseries.
    Raises CustomUploadError (or some subclass thereof) if anything goes
    wrong.
    """
    upload = DistUpgraderUpload(archive_root, tarfile_path, distroseries)
    upload.process()

# Copyright 2006 Canonical Ltd.  All rights reserved.

"""The processing of dist-upgrader tarballs."""

__metaclass__ = type

__all__ = ['process_dist_upgrader']

import os
import tarfile
import stat
import shutil

from canonical.archivepublisher.custom_upload import (
    CustomUpload, CustomUploadError)
from sourcerer.deb.version import (
    BadUpstreamError, Version as make_version)


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

    def __init__(self, archive_root, tarfile_path, distrorelease):
        CustomUpload.__init__(self, archive_root, tarfile_path, distrorelease)

        tarfile_base = os.path.basename(tarfile_path)
        name, self.version, arch = tarfile_base.split('_')
        arch = arch.split('.')[0]

        self.targetdir = os.path.join(archive_root, 'dists', distrorelease,
                                      'main', 'dist-upgrader-%s' % arch)

        # Make sure the target version doesn't already exist. If it does, raise
        # DistUpgraderAlreadyExists.
        if os.path.exists(os.path.join(self.targetdir, self.version)):
            raise DistUpgraderAlreadyExists(arch, self.version)

    def shouldInstall(self, filename):
        directory_name = filename.split('/')[0]
        try:
            version = make_version(directory_name)
        except BadUpstreamError, exc:
            raise DistUpgraderBadVersion(self.tarfile_path, exc)
        return version and not filename.startswith('current')


def process_dist_upgrader(archive_root, tarfile_path, distrorelease):
    """Process a raw-dist-upgrader tarfile.

    Unpacking it into the given archive for the given distrorelease.
    Raises CustomUploadError (or some subclass thereof) if anything goes
    wrong.
    """
    upload = DistUpgraderUpload(archive_root, tarfile_path, distrorelease)
    upload.process()

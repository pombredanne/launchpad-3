# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The processing of debian installer tarballs."""

# This code is mostly owned by Colin Watson and is partly refactored by
# Daniel Silverstone who should be the first point of contact for it.

__metaclass__ = type

__all__ = ['process_debian_installer']

import os
import shutil

from lp.archivepublisher.customupload import (
    CustomUpload,
    CustomUploadError,
    )


class DebianInstallerAlreadyExists(CustomUploadError):
    """A build for this type, architecture, and version already exists."""
    def __init__(self, build_type, arch, version):
        message = ('%s build %s for architecture %s already exists' %
                   (build_type, arch, version))
        CustomUploadError.__init__(self, message)


class DebianInstallerUpload(CustomUpload):
    """ Debian Installer custom upload.

    The debian-installer filename should be something like:

        <BASE>_<VERSION>_<ARCH>.tar.gz

    where:

      * BASE: base name (usually 'debian-installer-images');
      * VERSION: encoded version (something like '20061102ubuntu14');
      * if the version string contains '.0.' we assume it is a
        'daily-installer', otherwise, it is a normal 'installer';
      * ARCH: targeted architecture tag ('i386', 'amd64', etc);

    The contents are extracted in the archive, respecting its type
    ('installer' or 'daily-installer'), in the following path:

         <ARCHIVE>/dists/<SUITE>/main/<TYPE>-<ARCH>/<VERSION>

    A 'current' symbolic link points to the most recent version.
    """
    def __init__(self, archive_root, tarfile_path, distroseries):
        CustomUpload.__init__(self, archive_root, tarfile_path, distroseries)

        tarfile_base = os.path.basename(tarfile_path)
        components = tarfile_base.split('_')
        self.version = components[1]
        self.arch = components[2].split('.')[0]

        # Is this a full build or a daily build?
        if '.0.' not in self.version:
            build_type = 'installer'
        else:
            build_type = 'daily-installer'

        self.targetdir = os.path.join(
            archive_root, 'dists', distroseries, 'main',
            '%s-%s' % (build_type, self.arch))

        if os.path.exists(os.path.join(self.targetdir, self.version)):
            raise DebianInstallerAlreadyExists(
                build_type, self.arch, self.version)

    def extract(self):
        CustomUpload.extract(self)
        # We now have a valid unpacked installer directory, but it's one level
        # deeper than it should be. Move it up and remove the debris.
        unpack_dir = 'installer-%s' % self.arch
        os.rename(os.path.join(self.tmpdir, unpack_dir, self.version),
                  os.path.join(self.tmpdir, self.version))
        shutil.rmtree(os.path.join(self.tmpdir, unpack_dir))

    def shouldInstall(self, filename):
        return filename.startswith('%s/' % self.version)


def process_debian_installer(archive_root, tarfile_path, distroseries):
    """Process a raw-installer tarfile.

    Unpacking it into the given archive for the given distroseries.
    Raises CustomUploadError (or some subclass thereof) if anything goes
    wrong.
    """
    upload = DebianInstallerUpload(archive_root, tarfile_path, distroseries)
    upload.process()

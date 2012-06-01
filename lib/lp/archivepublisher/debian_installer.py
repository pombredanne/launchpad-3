# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""The processing of debian installer tarballs."""

# This code is mostly owned by Colin Watson and is partly refactored by
# Daniel Silverstone who should be the first point of contact for it.

__metaclass__ = type

__all__ = [
    'DebianInstallerUpload',
    'process_debian_installer',
    ]

import os
import shutil

from lp.archivepublisher.customupload import CustomUpload


class DebianInstallerUpload(CustomUpload):
    """ Debian Installer custom upload.

    The debian-installer filename should be something like:

        <BASE>_<VERSION>_<ARCH>.tar.gz

    where:

      * BASE: base name (usually 'debian-installer-images');
      * VERSION: encoded version (something like '20061102ubuntu14');
      * ARCH: targeted architecture tag ('i386', 'amd64', etc);

    The contents are extracted in the archive in the following path:

         <ARCHIVE>/dists/<SUITE>/main/installer-<ARCH>/<VERSION>

    A 'current' symbolic link points to the most recent version.
    """
    custom_type = "installer"

    def setTargetDirectory(self, archive_root, tarfile_path, distroseries):
        tarfile_base = os.path.basename(tarfile_path)
        _, self.version, self.arch = tarfile_base.split("_")
        self.arch = self.arch.split(".")[0]

        self.targetdir = os.path.join(
            archive_root, 'dists', distroseries, 'main',
            'installer-%s' % self.arch)

    @classmethod
    def getSeriesKey(cls, tarfile_path):
        try:
            _, _, arch = os.path.basename(tarfile_path).split("_")
            return arch.split(".")[0]
        except ValueError:
            return None

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
    upload = DebianInstallerUpload()
    upload.process(archive_root, tarfile_path, distroseries)

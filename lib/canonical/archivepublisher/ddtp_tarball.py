# Copyright 2006 Canonical Ltd.  All rights reserved.

"""The processing of translated packages descriptions (ddtp) tarballs.

DDTP (Debian Descripton Translation Project) aims to offer the description
of all supported packages translated in several languages.

DDTP-TARBALL is a custom format upload supported by Launchpad infrastructure
to enable developers to publish indexes of DDTP contents.
"""

__metaclass__ = type

__all__ = ['process_ddtp_tarball']

import os
import tarfile
import stat

from canonical.archivepublisher.customupload import CustomUpload


class DdtpTarballUpload(CustomUpload):
    """DDTP (Debian Description Translation Project) tarball upload

    The tarball should be name as:

     <NAME>_<COMPONENT>_<VERSION>.tar.gz

    where:

     * NAME: anything reasonable (ddtp-tarball);
     * COMPONENT: LP component (main, universe, etc);
     * VERSION: debian-like version token.

    It is consisted of a tarball containing all the supported indexes
    files for the DDTP system (under 'i18n' directory) contents driven
    by component.

    Results will be published (installed in archive) under:

       <ARCHIVE>dists/<SUITE>/<COMPONENT>/i18n

    Old contents will be preserved.
    """
    def __init__(self, archive_root, tarfile_path, distrorelease):
        CustomUpload.__init__(self, archive_root, tarfile_path, distrorelease)

        tarfile_base = os.path.basename(tarfile_path)
        name, component, self.version = tarfile_base.split('_')
        self.targetdir = os.path.join(archive_root, 'dists',
                                      distrorelease, component)

    def shouldInstall(self, filename):
        # Ignore files outside of the i18n subdirectory
        return filename.startswith('i18n/')

    def fixCurrentSymlink(self):
        # There is no symlink to fix up for DDTP uploads
        pass


def process_ddtp_tarball(archive_root, tarfile_path, distrorelease):
    """Process a raw-ddtp-tarball tarfile.

    Unpacking it into the given archive for the given distrorelease.
    Raises CustomUploadError (or some subclass thereof) if
    anything goes wrong.
    """
    upload = DdtpTarballUpload(archive_root, tarfile_path, distrorelease)
    upload.process()


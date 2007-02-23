# Copyright 2006 Canonical Ltd.  All rights reserved.

"""The processing of translated packages descriptions (ddtp) tarballs.

DDTP (Debian Descripton Translation Project) aims to offer the description
of all supported packages translated in several languages.

DDTP-TARBALL is a custom format upload supported by Launchpad infrastructure
to enable developers to publish indexes of DDTP contents.
"""

__metaclass__ = type

__all__ = ['process_ddtp_tarball', 'DddtpTarballError']

import os
import tarfile
import stat

from canonical.archivepublisher.custom_upload import CustomUpload


class DdtpTarballUpload(CustomUpload):

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
    Raises CustomUploadTarballError (or some subclass thereof) if
    anything goes wrong.
    """
    upload = DdtpTarballUpload(archive_root, tarfile_path, distrorelease)
    upload.process()


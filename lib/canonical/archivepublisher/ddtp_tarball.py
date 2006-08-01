# Copyright 2006 Canonical Ltd.  All rights reserved.

"""The processing of translated packages descriptions (ddtp) tarballs."""

__metaclass__ = type

__all__ = ['process_ddtp_tarball', 'DddtpTarballError']

import os
import tarfile
import stat
import shutil

from sourcerer.deb.version import Version as DebianVersion


class DdtpTarballError(Exception):
    """Base class for all errors associated with putting a translated
       package descriptions (ddtp) tarball on disk in the archive."""

class DdtpTarballTarError(DdtpTarballError):
    """The tarfile module raised an exception."""
    def __init__(self, tarfile_path, tar_error):
        message = 'Problem reading tarfile %s: %s' % (tarfile_path, tar_error)
        DdtpTarballError.__init__(self, message)
        self.tarfile_path = tarfile_path
        self.tar_error = tar_error

class DdtpTarballInvalidTarfile(DdtpTarballError):
    """The supplied tarfile did not contain the expected elements."""
    def __init__(self, tarfile_path, expected_dir):
        message = ('Tarfile %s did not contain expected file %s' %
                   (tarfile_path, expected_dir))
        DdtpTarballError.__init__(self, message)
        self.tarfile_path = tarfile_path
        self.expected_dir = expected_dir


def extract_filename_parts(tarfile_path):
    """Extract the basename, version and arch of the supplied ddtp tarfile."""
    tarfile_base = os.path.basename(tarfile_path)
    name, component, version = tarfile_base.split('_')
    return tarfile_base, component, version

def process_ddtp_tarball(archive_root, tarfile_path, distrorelease,
                          make_version=DebianVersion):
    """Process a ddtp tarfile, unpacking it into the given
    archive for the given distrorelease.

    make_version is a callable which converts version numbers into python
    objects which can be compared nicely. This defaults to sourcerer's version
    type for deb packages. It does exactly what we want for now.

    Raises DdtpTarballError (or some subclass thereof) if anything goes
    wrong.
    """

    tarfile_base, component, version = extract_filename_parts(tarfile_path)

    target = os.path.join(archive_root, 'dists', distrorelease, component)
    unpack_dir = 'i18n'

    # Unpack the tarball directly into the archive. Skip anything outside
    # unpack_dir. Make sure everything we extract
    # is group-writable. If we didn't extract anything, raise
    # DistUpgraderInvalidTarfile.
    tar = None
    extracted = False

    try:
        tar = tarfile.open(tarfile_path)
        try:
            for tarinfo in tar:
                if not tarinfo.name.startswith('i18n'):
                    continue
                tar.extract(tarinfo, target)
                newpath = os.path.join(target, tarinfo.name)
                mode = stat.S_IMODE(os.stat(newpath).st_mode)
                os.chmod(newpath, mode | stat.S_IWGRP)
                extracted = True
        finally:
            tar.close()
    except tarfile.TarError, e:
        raise DistUpgraderTarError(tarfile_path, e)

    if not extracted:
        raise DistUpgraderInvalidTarfile(tarfile_path, target)


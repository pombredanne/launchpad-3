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


class DdtpTarballError(Exception):
    """Base class for all errors associated with publishing ddtp indexes."""


class DdtpTarballTarError(DdtpTarballError):
    """The tarfile module raised an exception."""
    def __init__(self, tarfile_path, tar_error):
        message = 'Problem reading tarfile %s: %s' % (tarfile_path, tar_error)
        DdtpTarballError.__init__(self, message)


class DdtpTarballInvalidTarfile(DdtpTarballError):
    """The supplied tarfile did not contain the expected elements."""
    def __init__(self, tarfile_path, expected_dir):
        message = ('Tarfile %s did not contain expected file %s' %
                   (tarfile_path, expected_dir))
        DdtpTarballError.__init__(self, message)


def extract_filename_parts(tarfile_path):
    """Extract the basename, version and arch of the supplied ddtp tarfile."""
    tarfile_base = os.path.basename(tarfile_path)
    name, component, version = tarfile_base.split('_')
    return tarfile_base, component, version

def process_ddtp_tarball(archive_root, tarfile_path, distrorelease):
    """Process a raw-ddtp-tarball tarfile.

    Unpacking it into the given archive for the given distrorelease.
    Raises DdtpTarballError (or some subclass thereof) if anything goes
    wrong.
    """
    tarfile_base, component, version = extract_filename_parts(tarfile_path)
    target = os.path.join(archive_root, 'dists', distrorelease, component)

    # Unpack the tarball directly into the archive.
    # Skip anything outside 'i18n' directory.
    # Make sure everything we extract is group-writable.
    # If we didn't extract anything, raise DistUpgraderInvalidTarfile.
    extracted = False
    target_dir = 'i18n/'
    try:
        tar = tarfile.open(tarfile_path)
        try:
            for tarinfo in tar:
                name = os.path.normpath(tarinfo.name)
                # ignore files or directories outside target_dir
                if not name.startswith(target_dir):
                    continue
                # ignore directories inside target_dir; use tarinfo.name
                # here because normpath drops the trailing slash
                if tarinfo.isdir() and tarinfo.name != (target_dir):
                    continue
                # Workaround a problem of the tarfile lib when dealing
                # with hardlinks. tarfile.extract() doesn't remove the
                # destination file, it simply truncates it to position
                # zero and writes the new content.
                # If the destination is a hard link it ends up corrupting
                # contents. We've faced this in /dsync-ed/ production
                # archive. cprov 20060817
                newpath = os.path.join(target, name)
                # try to remove disk copy of incoming files,
                # (ignore <target_dir>, we only care about files).
                if tarinfo.isfile() and os.path.exists(newpath):
                    os.remove(newpath)

                tar.extract(tarinfo, target)
                mode = stat.S_IMODE(os.stat(newpath).st_mode)
                os.chmod(newpath, mode | stat.S_IWGRP)
            extracted = True
        finally:
            tar.close()
    except tarfile.TarError, e:
        raise DdtpTarballTarError(tarfile_path, e)

    if not extracted:
        raise DdtpTarballInvalidTarfile(tarfile_path, target)


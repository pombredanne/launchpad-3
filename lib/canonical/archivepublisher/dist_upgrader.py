# Copyright 2006 Canonical Ltd.  All rights reserved.

"""The processing of dist-upgrader tarballs."""

__metaclass__ = type

__all__ = ['process_dist_upgrader', 'DistUpgraderError']

import os
import tarfile
import stat
import shutil

from sourcerer.deb.version import Version as DebianVersion


class DistUpgraderError(Exception):
    """Base class for all errors associated with putting a dist-upgrader
       tarball on disk in the archive."""


class DistUpgraderAlreadyExists(DistUpgraderError):
    """A build for this type, version already exists."""
    def __init__(self, arch, version):
        message = ('dist-upgrader build %s for architecture %s already exists'%
                   (arch, version))
        DistUpgradeError.__init__(self, message)
        self.arch = arch
        self.version = version

class DistUpgraderTarError(DistUpgraderError):
    """The tarfile module raised an exception."""
    def __init__(self, tarfile_path, tar_error):
        message = 'Problem reading tarfile %s: %s' % (tarfile_path, tar_error)
        DistUpgraderError.__init__(self, message)
        self.tarfile_path = tarfile_path
        self.tar_error = tar_error


class DistUpgraderInvalidTarfile(DistUpgraderError):
    """The supplied tarfile did not contain the expected elements."""
    def __init__(self, tarfile_path, expected_dir):
        message = ('Tarfile %s did not contain expected file %s' %
                   (tarfile_path, expected_dir))
        DistUpgraderError.__init__(self, message)
        self.tarfile_path = tarfile_path
        self.expected_dir = expected_dir


def extract_filename_parts(tarfile_path):
    """Extract the basename, version and arch of the supplied d-i tarfile."""
    tarfile_base = os.path.basename(tarfile_path)
    name, version, arch = tarfile_base.split('_')
    arch = arch.split('.')[0]
    return tarfile_base, version, arch


def process_dist_upgrader(archive_root, tarfile_path, distrorelease,
                          make_version=DebianVersion):
    """Process a raw-dist-upgrader tarfile, unpacking it into the given
    archive for the given distrorelease.

    make_version is a callable which converts version numbers into python
    objects which can be compared nicely. This defaults to sourcerer's version
    type for deb packages. It does exactly what we want for now.

    Raises DistUpgraderError (or some subclass thereof) if anything goes
    wrong.
    """

    tarfile_base, version, arch = extract_filename_parts(tarfile_path)

    target = os.path.join(archive_root, 'dists', distrorelease, 'main',
                          'dist-upgrader-%s' % arch)
    unpack_dir = 'dist-upgrader-%s' % arch

    # Make sure the target version doesn't already exist. If it does, raise
    # DistUpgraderAlreadyExists.
    if os.path.exists(os.path.join(target, version)):
        raise DistUpgraderAlreadyExists(arch, version)

    # Unpack the tarball directly into the archive. Skip anything outside
    # unpack_dir/version, and skip the unpack_dir/current symlink (which
    # we'll fix up ourselves in a moment). Make sure everything we extract
    # is group-writable. If we didn't extract anything, raise
    # DistUpgraderInvalidTarfile.
    tar = None
    extracted = False

    try:
        tar = tarfile.open(tarfile_path)
        try:
            for tarinfo in tar:
                if tarinfo.name != os.path.join('current'):
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
        raise DistUpgraderInvalidTarfile(tarfile_path, expected_dir)

    # Get an appropriately-sorted list of the dist-upgrader directories now
    # present in the target.
    versions = [inst for inst in os.listdir(target) if inst != 'current']
    if make_version is not None:
        versions.sort(key=make_version, reverse=True)
    else:
        versions.reverse()

    # Make sure the 'current' symlink points to the most recent version
    # The most recent version is in versions[0]
    current = os.path.join(target, 'current')
    os.symlink(versions[0], '%s.new' % current)
    os.rename('%s.new' % current, current)

    # There may be some other unpacked dist-upgrader directories in the target
    # already. We only keep the three with the highest version (plus the one
    # we just extracted, if for some reason it's lower).
    for oldversion in versions[3:]:
        if oldversion != version:
            shutil.rmtree(os.path.join(target, oldversion))

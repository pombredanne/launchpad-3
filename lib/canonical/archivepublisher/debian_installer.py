# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""The processing of debian installer tarballs."""

# This code is mostly owned by Colin Watson and is partly refactored by
# Daniel Silverstone who should be the first point of contact for it.

__metaclass__ = type

__all__ = ['process_debian_installer', 'DebianInstallerError']

import os
import tarfile
import stat
import shutil

from sourcerer.deb.version import Version as DebianVersion


class DebianInstallerError(Exception):
    """Base class for all errors associated with putting a d-i tarball on
    disk in the archive."""


class DebianInstallerAlreadyExists(DebianInstallerError):
    """A build for this type, architecture, and version already exists."""
    def __init__(self, build_type, arch, version):
        message = ('%s build %s for architecture %s already exists' %
                   (build_type, arch, version))
        DebianInstallerError.__init__(self, message)
        self.build_type = build_type
        self.arch = arch
        self.version = version


class DebianInstallerTarError(DebianInstallerError):
    """The tarfile module raised an exception."""
    def __init__(self, tarfile_path, tar_error):
        message = 'Problem reading tarfile %s: %s' % (tarfile_path, tar_error)
        DebianInstallerError.__init__(self, message)
        self.tarfile_path = tarfile_path
        self.tar_error = tar_error


class DebianInstallerInvalidTarfile(DebianInstallerError):
    """The supplied tarfile did not contain the expected elements."""
    def __init__(self, tarfile_path, expected_dir):
        message = ('Tarfile %s did not contain expected directory %s' %
                   (tarfile_path, expected_dir))
        DebianInstallerError.__init__(self, message)
        self.tarfile_path = tarfile_path
        self.expected_dir = expected_dir


def extract_filename_parts(tarfile_path):
    """Extract the basename, version and arch of the supplied d-i tarfile."""
    tarfile_base = os.path.basename(tarfile_path)
    components = tarfile_base.split('_')
    version = components[1]
    arch = components[2].split('.')[0]
    return tarfile_base, version, arch


def process_debian_installer(archive_root, tarfile_path, distrorelease,
                             make_version=DebianVersion):
    """Process a raw-installer tarfile, unpacking it into the given archive
    for the given distrorelease.

    make_version is a callable which converts version numbers into python
    objects which can be compared nicely. This defaults to sourcerer's version
    type for deb packages. It does exactly what we want for now.

    Raises DebianInstallerError (or some subclass thereof) if anything goes
    wrong.
    """

    tarfile_base, version, arch = extract_filename_parts(tarfile_path)

    # Is this a full build or a daily build?
    if '.0.' not in version:
        build_type = 'installer'
    else:
        build_type = 'daily-installer'

    target = os.path.join(archive_root, 'dists', distrorelease, 'main',
                          '%s-%s' % (build_type, arch))
    unpack_dir = 'installer-%s' % arch

    # Make sure the target version doesn't already exist. If it does, raise
    # DebianInstallerAlreadyExists.
    if os.path.exists(os.path.join(target, version)):
        raise DebianInstallerAlreadyExists(build_type, arch, version)

    # Unpack the tarball directly into the archive. Skip anything outside
    # unpack_dir/version, and skip the unpack_dir/current symlink (which
    # we'll fix up ourselves in a moment). Make sure everything we extract
    # is group-writable. If we didn't extract anything, raise
    # DebianInstallerInvalidTarfile.
    expected_dir = os.path.join(unpack_dir, version)
    tar = None
    extracted = False
    try:
        try:
            tar = tarfile.open(tarfile_path)
            for tarinfo in tar:
                if (tarinfo.name.startswith('%s/' % expected_dir) and
                    tarinfo.name != os.path.join(unpack_dir, 'current')):
                    tar.extract(tarinfo, target)
                    newpath = os.path.join(target, tarinfo.name)
                    mode = stat.S_IMODE(os.stat(newpath).st_mode)
                    os.chmod(newpath, mode | stat.S_IWGRP)
                    extracted = True
        except tarfile.TarError, e:
            raise DebianInstallerTarError(tarfile_path, e)
    finally:
        if tar is not None:
            tar.close()
    if not extracted:
        raise DebianInstallerInvalidTarfile(tarfile_path, expected_dir)

    # We now have a valid unpacked installer directory, but it's one level
    # deeper than it should be. Move it up and remove the debris.
    shutil.move(os.path.join(target, expected_dir),
                os.path.join(target, version))
    shutil.rmtree(os.path.join(target, unpack_dir))

    # Get an appropriately-sorted list of the installer directories now
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

    # There may be some other unpacked installer directories in the target
    # already. We only keep the three with the highest version (plus the one
    # we just extracted, if for some reason it's lower).
    for oldversion in versions[3:]:
        if oldversion != version:
            shutil.rmtree(os.path.join(target, oldversion))

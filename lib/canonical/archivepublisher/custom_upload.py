# Copyright 2006 Canonical Ltd.  All rights reserved.

"""The processing of translated packages descriptions (ddtp) tarballs.

DDTP (Debian Descripton Translation Project) aims to offer the description
of all supported packages translated in several languages.

DDTP-TARBALL is a custom format upload supported by Launchpad infrastructure
to enable developers to publish indexes of DDTP contents.
"""

__metaclass__ = type

__all__ = ['CustomUpload', 'CustomUploadTarballError']

import os
import shutil
import stat
import tarfile
import tempfile

from sourcerer.deb.version import Version as make_version


class CustomUploadTarballError(Exception):
    """Base class for all errors associated with publishing custom uploads."""


class CustomUploadTarballTarError(CustomUploadTarballError):
    """The tarfile module raised an exception."""
    def __init__(self, tarfile_path, tar_error):
        message = 'Problem reading tarfile %s: %s' % (tarfile_path, tar_error)
        CustomUploadTarballError.__init__(self, message)


class CustomUploadTarballInvalidTarfile(CustomUploadTarballError):
    """The supplied tarfile did not contain the expected elements."""
    def __init__(self, tarfile_path, expected_dir):
        message = ('Tarfile %s did not contain expected file %s' %
                   (tarfile_path, expected_dir))
        CustomUploadTarballError.__init__(self, message)


class CustomUpload:

    # The following should be overriden by subclasses, probably in their __init__
    targetdir = None
    version = None

    def __init__(self, archive_root, tarfile_path, distrorelease):
        self.archive_root = archive_root
        self.tarfile_path = tarfile_path
        self.distrorelease = distrorelease

        self.tmpdir = None

    def process(self):
        try:
            self.extract()
            self.installFiles()
            self.fixCurrentSymlink()
        finally:
            self.cleanup()

    def extract(self):
        """Extract the custom upload to a temporary directory."""
        assert self.tmpdir is None, "Have already extracted tarfile"
        self.tmpdir = tempfile.mkdtemp(prefix='customupload_')
        try:
            tar = tarfile.open(self.tarfile_path)
            try:
                for tarinfo in tar:
                    tar.extract(tarinfo, self.tmpdir)
            finally:
                tar.close()
        except tarfile.TarError, exc:
            raise CustomUploadTarballTarError(self.tarfile_path, exc)

    def shouldInstall(self, filename):
        """Returns True if the given filename should be installed."""
        raise NotImplementedError

    def installFiles(self):
        assert self.tmpdir is not None, "Must extract tarfile first"
        extracted = False
        for dirpath, dirnames, filenames in os.walk(self.tmpdir):
            for filename in filenames:
                source = os.path.join(dirpath, filename)
                assert source.startswith(self.tmpdir)
                basepath = source[len(self.tmpdir):].lstrip(os.path.sep)
                dest = os.path.join(self.targetdir, basepath)

                if not self.shouldInstall(basepath):
                    continue
                # make sure the parent directory exists:
                parentdir = os.path.dirname(dest)
                if not os.path.isdir(parentdir):
                    os.makedirs(parentdir, mode=0775)
                # Remove any previous file, to avoid hard link problems
                if os.path.exists(dest):
                    os.remove(dest)
                # Copy the file or symlink
                if os.path.islink(source):
                    os.symlink(os.readlink(source), dest)
                else:
                    shutil.copy(source, dest)
                # Make the file group writable
                os.chmod(dest, 0664)
                extracted = True
        if not extracted:
            raise CustomUploadTarballInvalidTarfile(self.tarfile_path,
                                                    self.targetdir)

    def fixCurrentSymlink(self):
        """Update the 'current' symlink and prune old uploads from the tree."""
        # Get an appropriately-sorted list of the installer directories now
        # present in the target.
        versions = [inst for inst in os.listdir(self.targetdir)
                    if inst != 'current']
        versions.sort(key=make_version, reverse=True)

        # Make sure the 'current' symlink points to the most recent version
        # The most recent version is in versions[0]
        current = os.path.join(target, 'current')
        os.symlink(versions[0], '%s.new' % current)
        os.rename('%s.new' % current, current)

        # There may be some other unpacked installer directories in
        # the target already. We only keep the three with the highest
        # version (plus the one we just extracted, if for some reason
        # it's lower).
        for oldversion in versions[3:]:
            if oldversion != self.version:
                shutil.rmtree(os.path.join(target, oldversion))

    def cleanup(self):
        """Clean up the temporary directory"""
        if self.tmpdir is not None:
            shutil.rmtree(self.tmpdir, ignore_errors=True)
            self.tmpdir = None

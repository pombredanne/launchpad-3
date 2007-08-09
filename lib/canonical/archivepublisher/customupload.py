# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

"""Infrastructure for handling custom uploads.

Custom uploads are uploaded to Soyuz as special tarballs that must be
extracted to a particular location in the archive.  This module
contains code common to the different custom upload types.

Custom uploads include Debian installer packages, dist upgraders and
DDTP (Debian Description Translation Project) tarballs.
"""

__metaclass__ = type

__all__ = ['CustomUpload', 'CustomUploadError']

import os
import shutil
import stat
import tarfile
import tempfile

from canonical.archivepublisher.debversion import Version as make_version


class CustomUploadError(Exception):
    """Base class for all errors associated with publishing custom uploads."""


class CustomUploadTarballTarError(CustomUploadError):
    """The tarfile module raised an exception."""
    def __init__(self, tarfile_path, tar_error):
        message = 'Problem reading tarfile %s: %s' % (tarfile_path, tar_error)
        CustomUploadError.__init__(self, message)


class CustomUploadTarballInvalidTarfile(CustomUploadError):
    """The supplied tarfile did not contain the expected elements."""
    def __init__(self, tarfile_path, expected_dir):
        message = ('Tarfile %s did not contain expected file %s' %
                   (tarfile_path, expected_dir))
        CustomUploadError.__init__(self, message)


class CustomUploadBadUmask(CustomUploadError):
    """The environment's umask was incorrect."""
    def __init__(self, expected_umask, got_umask):
        message = 'Bad umask; expected %03o, got %03o' % (
            expected_umask, got_umask)
        CustomUploadError.__init__(self, message)


class CustomUpload:
    """Base class for custom upload handlers"""

    # The following should be overriden by subclasses, probably in
    # their __init__
    targetdir = None
    version = None

    def __init__(self, archive_root, tarfile_path, distrorelease):
        self.archive_root = archive_root
        self.tarfile_path = tarfile_path
        self.distrorelease = distrorelease

        self.tmpdir = None

    def process(self):
        """Process the upload and install it into the archive."""
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
            tar.ignore_zeros = True
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

    def _buildInstallPaths(self, basename, dirname):
        """Build and return paths used to install files.

        Return a triple containing: (sourcepath, basepath, destpath)
        Where:
         * sourcepath is the absolute path to the extracted location.
         * basepath is the relative path inside the target location.
         * destpath is the absolute path to the target location.
        """
        sourcepath = os.path.join(dirname, basename)
        assert sourcepath.startswith(self.tmpdir), (
            "Source path must refer to the extracted location.")
        basepath = sourcepath[len(self.tmpdir):].lstrip(os.path.sep)
        destpath = os.path.join(self.targetdir, basepath)

        return sourcepath, basepath, destpath

    def ensurePath(self, path):
        """Ensure the parent directory exists."""
        parentdir = os.path.dirname(path)
        if not os.path.isdir(parentdir):
            os.makedirs(parentdir, 0755)

    def installFiles(self):
        """Install the files from the custom upload to the archive."""
        assert self.tmpdir is not None, "Must extract tarfile first"
        extracted = False
        for dirpath, dirnames, filenames in os.walk(self.tmpdir):

            # Create symbolic links to directories.
            for dirname in dirnames:
                sourcepath, basepath, destpath = self._buildInstallPaths(
                    dirname, dirpath)

                if not self.shouldInstall(basepath):
                    continue

                self.ensurePath(destpath)
                # Also, ensure that the process has the expected umask.
                old_mask = os.umask(0)
                try:
                    if old_mask != 022:
                        raise CustomUploadBadUmask(022, old_mask)
                finally:
                    os.umask(old_mask)
                if os.path.islink(sourcepath):
                    os.symlink(os.readlink(sourcepath), destpath)

                # XXX cprov 2007-03-27: We don't want to create empty
                # directories, some custom formats rely on this, DDTP,
                # for instance. We may end up with broken links
                # but that's more an uploader fault than anything else.

            # Create/Copy files.
            for filename in filenames:
                sourcepath, basepath, destpath = self._buildInstallPaths(
                    filename, dirpath)

                if not self.shouldInstall(basepath):
                    continue

                self.ensurePath(destpath)
                # Remove any previous file, to avoid hard link problems
                if os.path.exists(destpath):
                    os.remove(destpath)
                # Copy the file or symlink
                if os.path.islink(sourcepath):
                    os.symlink(os.readlink(sourcepath), destpath)
                else:
                    shutil.copy(sourcepath, destpath)
                    os.chmod(destpath, 0644)

                extracted = True

        if not extracted:
            raise CustomUploadTarballInvalidTarfile(
                self.tarfile_path, self.targetdir)

    def fixCurrentSymlink(self):
        """Update the 'current' symlink and prune old uploads from the tree."""
        # Get an appropriately-sorted list of the installer directories now
        # present in the target.
        versions = [inst for inst in os.listdir(self.targetdir)
                    if inst != 'current']
        versions.sort(key=make_version, reverse=True)

        # Make sure the 'current' symlink points to the most recent version
        # The most recent version is in versions[0]
        current = os.path.join(self.targetdir, 'current')
        os.symlink(versions[0], '%s.new' % current)
        os.rename('%s.new' % current, current)

        # There may be some other unpacked installer directories in
        # the target already. We only keep the three with the highest
        # version (plus the one we just extracted, if for some reason
        # it's lower).
        for oldversion in versions[3:]:
            if oldversion != self.version:
                shutil.rmtree(os.path.join(self.targetdir, oldversion))

    def cleanup(self):
        """Clean up the temporary directory"""
        if self.tmpdir is not None:
            shutil.rmtree(self.tmpdir, ignore_errors=True)
            self.tmpdir = None

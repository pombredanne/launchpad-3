# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Miscellaneous functions for publisher."""

__metaclass__ = type

__all__ = [
    'RepositoryIndexFile',
    'get_ppa_reference',
    ]


import bz2
import gzip
import os
import stat
import tempfile

try:
    import lzma
except ImportError:
    from backports import lzma

from lp.soyuz.enums import (
    ArchivePurpose,
    IndexCompressionType,
    )
from lp.soyuz.interfaces.archive import default_name_by_purpose


def get_ppa_reference(ppa):
    """Return a text reference for the given PPA.

    * '<owner_name>' for default PPAs (the ones named 'ppa');
    * '<owner_name>-<ppa_name>' for named-PPAs.
    """
    assert ppa.purpose == ArchivePurpose.PPA, (
        'Only PPAs can use reference name.')

    if ppa.name != default_name_by_purpose.get(ArchivePurpose.PPA):
        return '%s-%s' % (ppa.owner.name, ppa.name)

    return ppa.owner.name


class PlainTempFile:

    # Enumerated identifier.
    compression_type = IndexCompressionType.UNCOMPRESSED
    # Filename suffix.
    suffix = ''
    # File path built on initialization.
    path = None

    def __init__(self, temp_root, filename, auto_open=True):
        self.temp_root = temp_root
        self.filename = filename + self.suffix

        if auto_open:
            self.open()

    def _buildFile(self, fd):
        return os.fdopen(fd, 'wb')

    def open(self):
        fd, self.path = tempfile.mkstemp(
            dir=self.temp_root, prefix='%s_' % self.filename)
        self._fd = self._buildFile(fd)

    def write(self, content):
        self._fd.write(content)

    def close(self):
        self._fd.close()

    def __del__(self):
        """Remove temporary file if it was left behind. """
        if self.path is not None and os.path.exists(self.path):
            os.remove(self.path)


class GzipTempFile(PlainTempFile):
    compression_type = IndexCompressionType.GZIP
    suffix = '.gz'

    def _buildFile(self, fd):
        return gzip.GzipFile(fileobj=os.fdopen(fd, "wb"))


class Bzip2TempFile(PlainTempFile):
    compression_type = IndexCompressionType.BZIP2
    suffix = '.bz2'

    def _buildFile(self, fd):
        os.close(fd)
        return bz2.BZ2File(self.path, mode='wb')


class XZTempFile(PlainTempFile):
    compression_type = IndexCompressionType.XZ
    suffix = '.xz'

    def _buildFile(self, fd):
        os.close(fd)
        return lzma.LZMAFile(self.path, mode='wb', format=lzma.FORMAT_XZ)


class RepositoryIndexFile:
    """Facilitates the publication of repository index files.

    It allows callsites to publish index files in different medias
    (plain, gzip, bzip2, and xz) transparently and atomically.
    """

    def __init__(self, path, temp_root, compressors=None):
        """Store repositories destinations and filename.

        The given 'temp_root' needs to exist; on the other hand, the
        directory containing 'path' will be created on `close` if it doesn't
        exist.

        Additionally creates the needed temporary files in the given
        'temp_root'.
        """
        if compressors is None:
            compressors = [IndexCompressionType.UNCOMPRESSED]

        self.root, filename = os.path.split(path)
        assert os.path.exists(temp_root), 'Temporary root does not exist.'

        self.index_files = []
        self.old_index_files = []
        for cls in (PlainTempFile, GzipTempFile, Bzip2TempFile, XZTempFile):
            if cls.compression_type in compressors:
                self.index_files.append(cls(temp_root, filename))
            else:
                self.old_index_files.append(
                    cls(temp_root, filename, auto_open=False))

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def write(self, content):
        """Write contents to all target medias."""
        for index_file in self.index_files:
            index_file.write(content)

    def close(self):
        """Close temporary media and atomically publish them.

        If necessary the given 'root' destination is created at this point.

        It also fixes the final files permissions making them readable and
        writable by their group and readable by others.
        """
        if os.path.exists(self.root):
            assert os.access(
                self.root, os.W_OK), "%s not writeable!" % self.root
        else:
            os.makedirs(self.root)

        for index_file in self.index_files:
            index_file.close()
            root_path = os.path.join(self.root, index_file.filename)
            os.rename(index_file.path, root_path)
            # XXX julian 2007-10-03
            # This is kinda papering over a problem somewhere that causes the
            # files to get created with permissions that don't allow
            # group/world read access.
            # See https://bugs.launchpad.net/soyuz/+bug/148471
            mode = stat.S_IMODE(os.stat(root_path).st_mode)
            os.chmod(root_path,
                     mode | stat.S_IWGRP | stat.S_IRGRP | stat.S_IROTH)

        # Remove files that may have been created by older versions of this
        # code.
        for index_file in self.old_index_files:
            root_path = os.path.join(self.root, index_file.filename)
            if os.path.exists(root_path):
                os.remove(root_path)

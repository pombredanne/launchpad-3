# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Components for exporting translation files."""

__metaclass__ = type

__all__ = [
    'ExportedTranslationFile',
    'ExportFileStorage',
    'TranslationExporter',
    'LaunchpadWriteTarFile',
    ]

import os
import tarfile
import tempfile
import time
from StringIO import StringIO
from zope.component import subscribers
from zope.interface import implements

from canonical.launchpad.interfaces import (
    IExportedTranslationFile, ITranslationExporter,
    ITranslationFormatExporter, TranslationFileFormat)


class ExportedTranslationFile:
    """See `IExportedTranslationFile`."""
    implements(IExportedTranslationFile)

    def __init__(self, content_file):
        self._content_file  = content_file
        self.content_type = None
        self.path = None
        self.file_extension = None

        # Go to the end of the file.
        self._content_file.seek(0, 2)
        self.size = self._content_file.tell()
        # Go back to the start of the file.
        self._content_file.seek(0)

    def read(self, *args, **kwargs):
        """See `IExportedTranslationFile`."""
        if 'size' in kwargs:
            return self._content_file.read(kwargs['size'])
        else:
            return self._content_file.read()

    def close(self):
        """See `IExportedTranslationFile`."""
        self._content_file.close()


class TranslationExporter:
    """See `ITranslationExporter`."""
    implements(ITranslationExporter)

    def getExportersForSupportedFileFormat(self, file_format):
        """See `ITranslationExporter`."""
        exporters_available = []
        for exporter in subscribers([self], ITranslationFormatExporter):
            if file_format in exporter.supported_source_formats:
                exporters_available.append(exporter)

        return exporters_available

    def getExporterProducingTargetFileFormat(self, file_format):
        """See `ITranslationExporter`."""
        for exporter in subscribers([self], ITranslationFormatExporter):
            if (exporter.format == file_format or
                (file_format == TranslationFileFormat.XPI and
                 exporter.format == TranslationFileFormat.XPIPO)):
                # XPIPO is a special case for XPI exports.
                return exporter

        return None

# A note about tarballs, StringIO and unicode. SQLObject returns unicode
# values for columns which are declared as StringCol. We have to be careful
# not to pass unicode instances to the tarfile module, because when the
# tarfile's filehandle is a StringIO object, the StringIO object gets upset
# later when we ask it for its value and it tries to join together its
# buffers. This is why the tarball code is sprinkled with ".encode('ascii')".
# If we get separate StringCol and UnicodeCol column types, we won't need this
# any longer.
# -- Dafydd Harries, 2005-04-07.

class LaunchpadWriteTarFile:
    """Convenience wrapper around the tarfile module.

    This class makes it convenient to generate tar files in various ways.
    """

    def __init__(self, stream):
        self.tarfile = tarfile.open('', 'w:gz', stream)
        self.closed = False

    @classmethod
    def files_to_stream(cls, files):
        """Turn a dictionary of files into a data stream."""
        buffer = tempfile.TemporaryFile()
        archive = cls(buffer)
        archive.add_files(files)
        archive.close()
        buffer.seek(0)
        return buffer

    @classmethod
    def files_to_string(cls, files):
        """Turn a dictionary of files into a data string."""
        return cls.files_to_stream(files).read()

    @classmethod
    def files_to_tarfile(cls, files):
        """Turn a dictionary of files into a tarfile object."""
        return tarfile.open('', 'r', cls.files_to_stream(files))

    def close(self):
        """Close the archive.

        After the archive is closed, the data written to the filehandle will
        be complete. The archive may not be appended to after it has been
        closed.
        """

        self.tarfile.close()
        self.closed = True

    def add_file(self, path, contents):
        """Add a file to the archive."""
        assert not self.closed, "Can't add a file to a closed archive"

        now = int(time.time())
        path_bits = path.split(os.path.sep)

        # Ensure that all the directories in the path are present in the
        # archive.
        for i in range(1, len(path_bits)):
            joined_path = os.path.join(*path_bits[:i])

            try:
                self.tarfile.getmember(joined_path + os.path.sep)
            except KeyError:
                tarinfo = tarfile.TarInfo(joined_path)
                tarinfo.type = tarfile.DIRTYPE
                tarinfo.mtime = now
                tarinfo.mode = 0755
                tarinfo.uname = 'launchpad'
                tarinfo.gname = 'launchpad'
                self.tarfile.addfile(tarinfo)

        tarinfo = tarfile.TarInfo(path)
        tarinfo.time = now
        tarinfo.mtime = now
        tarinfo.mode = 0644
        tarinfo.size = len(contents)
        tarinfo.uname = 'launchpad'
        tarinfo.gname = 'launchpad'
        self.tarfile.addfile(tarinfo, StringIO(contents))

    def add_files(self, files):
        """Add a number of files to the archive.

        :param files: A dictionary mapping file names to file contents.
        """

        for filename in sorted(files.keys()):
            self.add_file(filename, files[filename])


class StorageStrategy:
    """Implementation strategy for `ExportFileStorage`.

    Storage for single files is implemented by `SingleFileStorageStrategy`;
    multiple files go into a `TarballFileStorageStrategy`.
    """
    def addFile(self, path, extension, content):
        """Add a file to be stored."""
        raise NotImplementedError()

    def isEmpty(self):
        """Is this storage object still devoid of files?"""
        raise NotImplementedError()

    def isFull(self):
        """Does this storage object have its fill of files?"""
        raise NotImplementedError()

    def export(self):
        raise NotImplementedError()


class SingleFileStorageStrategy(StorageStrategy):
    """Store a single file for export.

    Provides a way to store a single PO or POT file, but through the same API
    that `TarballFileStorageStrategy` offers to store any number of files into
    a single tarball.  Both classes have an `addFile` operation, though a
    `SingleFileStorageStrategy` instance will only let you add a single file.

    (The type of the stored file matters in this strategy because the storage
    strategy declares the MIME type of the file it produces).
    """

    path = None
    extension = None
    mimetype = None

    def __init__(self, mimetype):
        self.mimetype = mimetype

    def addFile(self, path, extension, content):
        """See `StorageStrategy`."""
        assert path is not None, "Storing file without path."
        assert self.path is None, "Multiple files added; expected just one."
        self.path = path
        self.extension = extension
        self.content = content

    def isEmpty(self):
        """See `StorageStrategy`."""
        return self.path is None

    def isFull(self):
        """See `StorageStrategy`.

        A `SingleFileStorageStrategy` can only store one file.
        """
        return not self.isEmpty()

    def export(self):
        """See `StorageStrategy`."""
        assert self.path is not None, "Exporting empty file."
        output = ExportedTranslationFile(StringIO(self.content))
        output.path = self.path
        # We use x-po for consistency with other .po editors like GTranslator.
        output.content_type = self.mimetype
        output.file_extension = self.extension
        return output


class TarballFileStorageStrategy(StorageStrategy):
    """Store any number of files for export as a tarball.

    Similar to `SingleFileStorageStrategy`, but lets you store any number of
    files using the same API.  Each file is written into the resulting tarball
    as soon as it is added.  There is no need to keep the full contents of the
    tarball in memory at any single time.
    """
    empty = False

    def __init__(self, single_file_storage=None):
        """Initialze empty storage strategy, or subsume single-file one."""
        self.buffer = tempfile.TemporaryFile()
        self.tar_writer = LaunchpadWriteTarFile(self.buffer)
        if single_file_storage is not None:
            self.addFile(single_file_storage.path,
                single_file_storage.extension, single_file_storage.content)

    def addFile(self, path, extension, content):
        """See `StorageStrategy`."""
        self.empty = False
        self.tar_writer.add_file(path, content)

    def isEmpty(self):
        """See `StorageStrategy`."""
        return self.empty

    def isFull(self):
        """See `StorageStrategy`.

        A `TarballFileStorageStrategy` can store any number of files, so no.
        """
        return False

    def export(self):
        """See `StorageStrategy`."""
        self.tar_writer.close()
        self.buffer.seek(0)
        output = ExportedTranslationFile(self.buffer)

        # Don't set path; let the caller decide.

        # For tar.gz files, the standard content type is application/x-gtar.
        # You can see more info on
        #   http://en.wikipedia.org/wiki/List_of_archive_formats
        output.content_type = 'application/x-gtar'
        output.file_extension = 'tar.gz'
        return output


class ExportFileStorage:
    """Store files to export, either as tarball or plain single file."""
    def __init__(self, mimetype):
        # Start out with a single file.  We can replace that strategy later if
        # we get more than one file.
        self._store = SingleFileStorageStrategy(mimetype)

    def addFile(self, path, extension, content):
        """Add file to be stored.

        :param path: location and name of this file, relative to root of tar
            archive.
        :param extension: filename suffix (ignored here).
        :param content: contents of file.
        """
        if self._store.isFull():
            # We're still using a single-file storage strategy, but we just
            # received our second file.  Switch to tarball strategy.
            self._store = TarballFileStorageStrategy(self._store)
        self._store.addFile(path, extension, content)

    def export(self):
        """Export as `ExportedTranslationFile`."""
        assert not self._store.isEmpty(), "Got empty list of files to export."
        return self._store.export()


# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Components for exporting translation files."""

__metaclass__ = type

__all__ = [
    'ExportedTranslationFile',
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
    ITranslationFormatExporter)


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
            if exporter.format == file_format:
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

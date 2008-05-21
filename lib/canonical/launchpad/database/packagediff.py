# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'PackageDiff',
    'PackageDiffSet',
    ]

import os
import shutil
from subprocess import Popen
import tempfile

from zope.component import getUtility
from zope.interface import implements
from sqlobject import ForeignKey

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    IPackageDiff, IPackageDiffSet)
from canonical.librarian.interfaces import ILibrarianClient


def perform_deb_diff(tmp_dir, out_filename, from_files, to_files):
    """Perform a (deb)diff on two packages.

    A debdiff will be invoked on the files associated with the
    two packages to be diff'ed. The resulting output will be
    written to 'out_filename'.

    :param tmp_dir: The temporary directory with the package files.
    :type tmp_dir: ``str``
    :param out_filename: The name of the file that will hold the
        resulting debdiff output.
    :type tmp_dir: ``str``
    :param from_files: A list with the names of the files associated
        with the first package.
    :type from_files: ``list``
    :param to_files: A list with the names of the files associated
        with the second package.
    :type to_files: ``list``
    """
    compressed_bytes = -1
    [from_dsc] = [name for name in from_files
                  if name.lower().endswith('.dsc')]
    [to_dsc] = [name for name in to_files
                if name.lower().endswith('.dsc')]
    args = ['debdiff', from_dsc, to_dsc]

    full_path = os.path.join(tmp_dir, out_filename)
    out_file = None
    try:
        out_file = open(full_path, 'w')

        # Create a child process for debdiff.
        child = Popen(args, stdout=out_file, cwd=tmp_dir)
        # Wait for debdiff to complete.
        returncode = child.wait()

        assert returncode == 0, 'Internal error: failed to run debdiff.'
    finally:
        if out_file is not None:
            out_file.close()

    # At this point the debdiff run has concluded and we have a diff
    # file that needs to be compressed.
    args = ['gzip', out_filename]

    # Create a child process for gzip.
    child = Popen(args, cwd=tmp_dir)
    # Wait for gzip to complete.
    returncode = child.wait()
    assert returncode == 0, 'Internal error: failed to run gzip.'

    return os.path.getsize(full_path + '.gz')

def download_file(destination_path, libraryfile):
    """Download a file from the librarian to the destination path.

    :param destination_path: Absolute destination path (where the
        file should be downloaded to).
    :type destination_path: ``str``
    :param libraryfile: The librarian file that is to be downloaded.
    :type libraryfile: ``LibraryFileAlias``
    """
    # We will download librarian files in 256 Kb chunks in order
    # to avoid excessive memory usage.
    chunksize = 256*1024

    destination_file = None
    try:
        libraryfile.open()
        destination_file = open(destination_path, 'w')
        chunk = libraryfile.read(chunksize)
        while chunk:
            destination_file.write(chunk)
            chunk = libraryfile.read(chunksize)
    finally:
        libraryfile.close()
        if destination_file is not None:
            destination_file.close()


class PackageDiff(SQLBase):
    """A Package Diff request."""

    implements(IPackageDiff)

    _defaultOrder = ['id']

    date_requested = UtcDateTimeCol(notNull=False, default=UTC_NOW)

    requester = ForeignKey(
        dbName='requester', foreignKey='Person', notNull=True)

    from_source = ForeignKey(
        dbName="from_source", foreignKey='SourcePackageRelease', notNull=True)

    to_source = ForeignKey(
        dbName="to_source", foreignKey='SourcePackageRelease', notNull=True)

    date_fulfilled = UtcDateTimeCol(notNull=False, default=None)

    diff_content = ForeignKey(
        dbName="diff_content", foreignKey='LibraryFileAlias',
        notNull=False, default=None)

    @property
    def title(self):
        """See `IPackageDiff`."""
        return 'Package diff from %s to %s' % (
            self.from_source.title, self.to_source.title)

    def performDiff(self):
        """See `IPackageDiff`.

        This involves creating a temporary directory, downloading the files
        from both SPRs involved from the librarian, running debdiff, storing
        the output in the librarian and updating the PackageDiff record.
        """
        # Create the temporary directory where the files will be
        # downloaded to and where the debdiff will be performed.
        tmp_dir = tempfile.mkdtemp()

        try:
            directions = ('from', 'to')

            # Keep track of the files belonging to the respective packages.
            downloaded = dict(zip(directions, ([], [])))

            # Please note that packages may have files in common.
            files_seen = []

            # Make it easy to iterate over packages.
            packages = dict(
                zip(directions, (self.from_source, self.to_source)))

            # Iterate over the packages to be diff'ed.
            for direction, package in packages.iteritems():
                # Download the files associated with each package.
                for file in package.files:
                    the_name = file.libraryfile.filename
                    # Was this file downloaded already?
                    if the_name in files_seen:
                        # Yes, skip it.
                        continue

                    # This file is new, download it.
                    destination_path = os.path.join(tmp_dir, the_name)
                    download_file(destination_path, file.libraryfile)
                    downloaded[direction].append(the_name)
                    files_seen.append(the_name)

            # All downloads are done. Construct the name of the resulting
            # diff file.
            result_filename = '%s-%s.%s-%s.diff' % (
                self.from_source.sourcepackagename.name,
                self.from_source.version,
                self.to_source.sourcepackagename.name,
                self.to_source.version)

            # Perform the actual diff operation.
            compressed_bytes = perform_deb_diff(
                tmp_dir, result_filename, downloaded['from'],
                downloaded['to'])

            # The diff file is ready and gzip'ed.
            result_filename += '.gz'
            result_path = os.path.join(tmp_dir, result_filename)

            # Upload the diff result file to the librarian.
            result_file = None
            try:
                result_file = open(result_path)
                self.diff_content = getUtility(ILibrarianClient).addFile(
                    result_filename, compressed_bytes, result_file,
                    'application/gzipped-patch')
            finally:
                if result_file is not None:
                    result_file.close()

            # Last but not least set the "date fulfilled" time stamp.
            self.date_fulfilled = UTC_NOW
        finally:
            shutil.rmtree(tmp_dir)


class PackageDiffSet:
    """This class is to deal with Distribution related stuff"""

    implements(IPackageDiffSet)

    def __iter__(self):
        """See `IPackageDiffSet`."""
        return iter(PackageDiff.select(orderBy=['-id']))

    def get(self, diff_id):
        """See `IPackageDiffSet`."""
        return PackageDiff.get(diff_id)

    def getPendingDiffs(self, limit=None):
        query = """
            date_fulfilled IS NULL
        """
        return PackageDiff.select(
            query, limit=limit, orderBy=['id'])

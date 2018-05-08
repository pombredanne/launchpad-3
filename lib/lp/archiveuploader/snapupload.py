# Copyright 2015-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Process a snap package upload."""

__metaclass__ = type

import os

import scandir
from zope.component import getUtility

from lp.archiveuploader.utils import UploadError
from lp.buildmaster.enums import BuildStatus
from lp.services.helpers import filenameToContentType
from lp.services.librarian.interfaces import ILibraryFileAliasSet


class SnapUpload:
    """A snap package upload.

    Unlike package uploads, these have no .changes files.  We simply attach
    all the files in the upload directory to the appropriate `ISnapBuild`.
    """

    def __init__(self, upload_path, logger):
        """Create a `SnapUpload`.

        :param upload_path: A directory containing files to upload.
        :param logger: The logger to be used.
        """
        self.upload_path = upload_path
        self.logger = logger

        self.librarian = getUtility(ILibraryFileAliasSet)

    def process(self, build):
        """Process this upload, loading it into the database."""
        self.logger.debug("Beginning processing.")

        found_snap = False
        snap_paths = []
        for dirpath, _, filenames in scandir.walk(self.upload_path):
            if dirpath == self.upload_path:
                # All relevant files will be in a subdirectory.
                continue
            for snap_file in sorted(filenames):
                if snap_file.endswith(".snap"):
                    found_snap = True
                snap_paths.append(os.path.join(dirpath, snap_file))

        if not found_snap:
            raise UploadError("Build did not produce any snap packages.")

        for snap_path in snap_paths:
            libraryfile = self.librarian.create(
                os.path.basename(snap_path), os.stat(snap_path).st_size,
                open(snap_path, "rb"),
                filenameToContentType(snap_path),
                restricted=build.is_private)
            build.addFile(libraryfile)

        # The master verifies the status to confirm successful upload.
        self.logger.debug("Updating %s" % build.title)
        build.updateStatus(BuildStatus.FULLYBUILT)

        self.logger.debug("Finished upload.")

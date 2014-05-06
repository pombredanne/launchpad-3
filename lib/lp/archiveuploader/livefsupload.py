# Copyright 2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Process a live filesystem upload."""

__metaclass__ = type

import os

from zope.component import getUtility

from lp.buildmaster.enums import BuildStatus
from lp.services.librarian.interfaces import ILibraryFileAliasSet


filename_ending_content_type_map = {
    ".manifest": "text/plain",
    ".manifest-remove": "text/plain",
    ".size": "text/plain",
    }


def get_livefs_content_type(path):
    for content_type_map in filename_ending_content_type_map.items():
        ending, content_type = content_type_map
        if path.endswith(ending):
            return content_type
    return "application/octet-stream"


class LiveFSUpload:
    """A live filesystem upload.

    Unlike package uploads, these have no .changes files.  We simply attach
    all the files in the upload directory to the appropriate `ILiveFSBuild`.
    """

    def __init__(self, upload_path, logger):
        """Create a `LiveFSUpload`.

        :param upload_path: A directory containing files to upload.
        :param logger: The logger to be used.
        """
        self.upload_path = upload_path
        self.logger = logger

        self.librarian = getUtility(ILibraryFileAliasSet)

    def process(self, build):
        """Process this upload, loading it into the database."""
        self.logger.debug("Beginning processing.")

        for dirpath, _, filenames in os.walk(self.upload_path):
            if dirpath == self.upload_path:
                # All relevant files will be in a subdirectory; this is a
                # simple way to avoid uploading any .distro file that may
                # exist.
                continue
            for livefs_file in sorted(filenames):
                livefs_path = os.path.join(dirpath, livefs_file)
                libraryfile = self.librarian.create(
                    livefs_file, os.stat(livefs_path).st_size,
                    open(livefs_path, "rb"),
                    get_livefs_content_type(livefs_path),
                    restricted=build.archive.private)
                build.addFile(libraryfile)

        # The master verifies the status to confirm successful upload.
        self.logger.debug("Updating %s" % build.title)
        build.updateStatus(BuildStatus.FULLYBUILT)

        self.logger.debug("Finished upload.")

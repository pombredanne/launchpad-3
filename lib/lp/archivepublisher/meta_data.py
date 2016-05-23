# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Processing of archive meta-data uploads."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    "MetaDataUpload",
    ]

import os

from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.customupload import CustomUpload
from lp.services.librarian.utils import copy_and_close


class MetaDataUpload(CustomUpload):
    """Meta-data custom upload.

    Meta-data custom files are published, unmodified, to a special area
    outside the actual archive directory.  This is so that the files can be
    seen even when the archive is private, and allows commercial customers
    to browse contents for potential later purchase.
    """
    custom_type = "meta-data"

    @classmethod
    def publish(cls, packageupload, libraryfilealias, logger=None):
        """See `ICustomUploadHandler`."""
        upload = cls(logger=logger)
        upload.process(packageupload, libraryfilealias)

    def process(self, packageupload, libraryfilealias):
        pubconf = getPubConfig(packageupload.archive)
        if pubconf.metaroot is None:
            if self.logger is not None:
                self.logger.debug(
                    "Skipping meta-data for archive without metaroot.")
            return

        dest_file = os.path.join(pubconf.metaroot, libraryfilealias.filename)
        if not os.path.isdir(pubconf.metaroot):
            os.makedirs(pubconf.metaroot, 0o755)

        # At this point we now have a directory of the format:
        # <person_name>/meta/<ppa_name>
        # We're ready to copy the file out of the librarian into it.

        file_obj = open(dest_file, "wb")
        libraryfilealias.open()
        copy_and_close(libraryfilealias, file_obj)

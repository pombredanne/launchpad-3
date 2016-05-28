# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Processing of static translations uploads."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    "StaticTranslationsUpload",
    ]

from lp.archivepublisher.customupload import CustomUpload


class StaticTranslationsUpload(CustomUpload):
    """Static translations upload.

    Static translations are not published.  Currently, they're only exposed
    via webservice methods so that third parties can retrieve them from the
    librarian.
    """
    custom_type = "static-translations"

    @classmethod
    def publish(cls, packageupload, libraryfilealias, logger=None):
        """See `ICustomUploadHandler`."""
        if logger is not None:
            logger.debug("Skipping publishing of static translations.")

    def process(self, packageupload, libraryfilealias):
        pass

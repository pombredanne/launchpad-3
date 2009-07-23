# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Permissions for uploading a package to an archive."""

__metaclass__ = type
__all__ = [
    'CannotUploadToArchive',
    'verify_upload',
    ]

from lp.soyuz.interfaces.archive import ArchivePurpose


class CannotUploadToArchive(Exception):
    """Raised when a person cannot upload to archive."""

    def __init__(self, person, archive):
        """Construct a `CannotUploadToArchive`.

        :param person: The person trying to get at the archive.
        :param archive: The archive.
        """
        Exception.__init__(
            self, '%s has no upload rights to %s' % (person, archive))


def verify_upload(person, suite_sourcepackage, archive):
    if archive.purpose == ArchivePurpose.PPA:
        if not archive.canUpload(person):
            raise CannotUploadToArchive(person, archive)

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Permissions for uploading a package to an archive."""

__metaclass__ = type
__all__ = [
    'CannotUploadToArchive',
    'verify_upload',
    ]

from zope.component import getUtility

from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.archivepermission import IArchivePermissionSet


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
    # For PPAs...
    if archive.purpose == ArchivePurpose.PPA:
        if not archive.canUpload(person):
            raise CannotUploadToArchive(person, archive)
        else:
            return True

    # For any other archive...
    spn = suite_sourcepackage.sourcepackagename
    ap_set = getUtility(IArchivePermissionSet)
    if not (
        archive.canUpload(person, spn)
        or ap_set.isSourceUploadAllowed(archive, spn, person)):
        raise CannotUploadToArchive(person, archive)

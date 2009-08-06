# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Permissions for uploading a package to an archive."""

__metaclass__ = type
__all__ = [
    'CannotUploadToArchive',
    'components_valid_for',
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


def components_valid_for(archive, person):
    permission_set = getUtility(IArchivePermissionSet)
    permissions = permission_set.componentsForUploader(archive, person)
    return set(permission.component for permission in permissions)


def verify_upload(person, suite_sourcepackage, archive,
                  strict_component=True):
    # For PPAs...
    if archive.purpose == ArchivePurpose.PPA:
        if not archive.canUpload(person):
            raise CannotUploadToArchive(person, archive)
        else:
            return True

    # For any other archive...
    spn = suite_sourcepackage.sourcepackagename
    ap_set = getUtility(IArchivePermissionSet)
    if (archive.canUpload(person, spn)
        or ap_set.isSourceUploadAllowed(archive, spn, person)):
        return

    component = suite_sourcepackage.sourcepackage.latest_published_component
    if component is not None:
        if strict_component:
            if archive.canUpload(person, component):
                return
        else:
            if len(components_valid_for(archive, person)) != 0:
                return
    raise CannotUploadToArchive(person, archive)

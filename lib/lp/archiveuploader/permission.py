# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Permissions for uploading a package to an archive."""

__metaclass__ = type
__all__ = [
    'CannotUploadToArchive',
    'CannotUploadToPPA',
    'components_valid_for',
    'verify_upload',
    ]

from zope.component import getUtility

from lp.soyuz.interfaces.archivepermission import IArchivePermissionSet


class CannotUploadToArchive(Exception):
    """Raised when a person cannot upload to archive."""

    _fmt = '%(person)s has no upload rights to %(archive)s.'

    def __init__(self, **args):
        """Construct a `CannotUploadToArchive`."""
        Exception.__init__(self, self._fmt % args)


class CannotUploadToPPA(CannotUploadToArchive):
    """Raised when a person cannot upload to a PPA."""

    _fmt = 'Signer has no upload rights to this PPA.'


class NoRightsForArchive(CannotUploadToArchive):
    """Raised when a person has absolutely no upload rights to an archive."""

    _fmt = (
        "The signer of this package has no upload rights to this "
        "distribution's primary archive.  Did you mean to upload to "
        "a PPA?")


class NoRightsForComponent(CannotUploadToArchive):
    """Raised when a person tries to upload to a component without permission.
    """

    _fmt = (
        "Signer is not permitted to upload to the component '%(component)s'.")

    def __init__(self, component):
        CannotUploadToArchive.__init__(self, component=component.name)


def components_valid_for(archive, person):
    """Return the components that 'person' can upload to 'archive'.

    :param archive: The `IArchive` than 'person' wishes to upload to.
    :param person: An `IPerson` wishing to upload to an archive.
    :return: A `set` of `IComponent`s that 'person' can upload to.
    """
    permission_set = getUtility(IArchivePermissionSet)
    permissions = permission_set.componentsForUploader(archive, person)
    return set(permission.component for permission in permissions)


def verify_upload(person, sourcepackagename, archive, component,
                  strict_component=True):
    """Can 'person' upload 'sourcepackagename' to 'archive'?

    :param person: The `IPerson` trying to upload to the package. Referred to
        as 'the signer' in upload code.
    :param sourcepackagename: The source package being uploaded. None if the
        package is new.
    :param archive: The `IArchive` being uploaded to.
    :param component: The `IComponent` that the source package belongs to.
    :param strict_component: True if access to the specific component for the
        package is needed to upload to it. If False, then access to any
        package will do.
    :raise CannotUploadToArchive: If 'person' cannot upload to the archive.
    :return: Nothing of interest.
    """
    # For PPAs...
    if archive.isPPA:
        if not archive.canUpload(person):
            raise CannotUploadToPPA()
        else:
            return True

    # For any other archive...
    ap_set = getUtility(IArchivePermissionSet)
    if sourcepackagename is not None and (
        archive.canUpload(person, sourcepackagename)
        or ap_set.isSourceUploadAllowed(archive, sourcepackagename, person)):
        return True

    if not components_valid_for(archive, person):
        raise NoRightsForArchive()

    if (component is not None
        and strict_component
        and not archive.canUpload(person, component)):
        raise NoRightsForComponent(component)

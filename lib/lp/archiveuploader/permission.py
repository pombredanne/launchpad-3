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

from lp.registry.interfaces.distribution import IDistributionSet
from lp.soyuz.interfaces.archivepermission import IArchivePermissionSet


class CannotUploadToArchive:
    """A reason for not being able to upload to an archive."""

    _fmt = '%(person)s has no upload rights to %(archive)s.'

    def __init__(self, **args):
        """Construct a `CannotUploadToArchive`."""
        self._message = self._fmt % args

    def __str__(self):
        return self._message


class CannotUploadToPPA(CannotUploadToArchive):
    """Raised when a person cannot upload to a PPA."""

    _fmt = 'Signer has no upload rights to this PPA.'


class NoRightsForArchive(CannotUploadToArchive):
    """Raised when a person has absolutely no upload rights to an archive."""

    _fmt = (
        "The signer of this package has no upload rights to this "
        "distribution's primary archive.  Did you mean to upload to "
        "a PPA?")


class InsufficientUploadRights(CannotUploadToArchive):
    """Raised when a person has insufficient upload rights."""
    _fmt = (
        "The signer of this package is lacking the upload rights for "
        "the source package, component or package set in question.")


class NoRightsForComponent(CannotUploadToArchive):
    """Raised when a person tries to upload to a component without permission.
    """

    _fmt = (
        "Signer is not permitted to upload to the component '%(component)s'.")

    def __init__(self, component):
        super(NoRightsForComponent, self).__init__(component=component.name)


def components_valid_for(archive, person):
    """Return the components that 'person' can upload to 'archive'.

    :param archive: The `IArchive` than 'person' wishes to upload to.
    :param person: An `IPerson` wishing to upload to an archive.
    :return: A `set` of `IComponent`s that 'person' can upload to.
    """
    permission_set = getUtility(IArchivePermissionSet)
    permissions = permission_set.componentsForUploader(archive, person)
    return set(permission.component for permission in permissions)


def packagesets_valid_for(archive, person):
    """Return the package sets that 'person' can upload to 'archive'.

    :param archive: The `IArchive` than 'person' wishes to upload to.
    :param person: An `IPerson` wishing to upload to an archive.
    :return: A `set` of `IPackageset`s that 'person' can upload to.
    """
    permission_set = getUtility(IArchivePermissionSet)
    permissions = permission_set.packagesetsForUploader(archive, person)
    return set(permission.packageset for permission in permissions)


def verify_upload(person, sourcepackagename, archive, component,
                  strict_component=True, distroseries=None):
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
    :return: CannotUploadToArchive if 'person' cannot upload to the archive,
        None otherwise.
    """
    # For PPAs...
    if archive.is_ppa:
        if not archive.canUpload(person):
            return CannotUploadToPPA()
        else:
            return None

    # For any other archive...

    # If the user did not specify the distro series, assume it is the current
    # one.
    if distroseries is None:
        ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        distroseries = ubuntu.currentseries

    ap_set = getUtility(IArchivePermissionSet)

    if sourcepackagename is not None:
        # Check whether user may upload because he holds a permission for
        #   - the given source package directly
        #   - a package set in the correct distro series that includes the
        #     given source package
        if (archive.canUpload(person, sourcepackagename) or
            ap_set.isSourceUploadAllowed(
                archive, sourcepackagename, person, distroseries)):
            return None

    if not components_valid_for(archive, person):
        if not packagesets_valid_for(archive, person):
            return NoRightsForArchive()
        else:
            return InsufficientUploadRights()

    if (component is not None
        and strict_component
        and not archive.canUpload(person, component)):
        return NoRightsForComponent(component)

    return None

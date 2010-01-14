# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Permissions for uploading a package to an archive."""

__metaclass__ = type
__all__ = [
    'CannotUploadToArchive',
    'CannotUploadToPPA',
    'can_upload_to_archive',
    'check_upload_to_archive',
    'components_valid_for',
    'verify_upload',
    ]

from zope.component import getUtility

from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.interfaces.archivepermission import IArchivePermissionSet
from lp.soyuz.interfaces.archive import ArchivePurpose


class CannotUploadToArchive(Exception):
    """A reason for not being able to upload to an archive."""

    _fmt = '%(person)s has no upload rights to %(archive)s.'

    def __init__(self, **args):
        """Construct a `CannotUploadToArchive`."""
        Exception.__init__(self, self._fmt % args)


class CannotUploadToPocket(Exception):
    """Returned when a pocket is closed for uploads."""

    def __init__(self, distroseries, pocket):
        Exception.__init__(self,
            "Not permitted to upload to the %s pocket in a series in the "
            "'%s' state." % (pocket.name, distroseries.status.name))


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
        CannotUploadToArchive.__init__(self, component=component.name)


class InvalidPocketForPPA(CannotUploadToArchive):
    """PPAs only support some pockets."""

    _fmt = "PPA uploads must be for the RELEASE pocket."


class InvalidPocketForPartnerArchive(CannotUploadToArchive):
    """Partner archives only support some pockets."""

    _fmt = "Partner uploads must be for the RELEASE or PROPOSED pocket."


class ArchiveDisabled(CannotUploadToArchive):
    """Uploading to a disabled archive is not allowed."""

    _fmt = ("%(archive_name)s is disabled.")

    def __init__(self, archive_name):
        CannotUploadToArchive.__init__(self, archive_name=archive_name)


def components_valid_for(archive, person):
    """Return the components that 'person' can upload to 'archive'.

    :param archive: The `IArchive` than 'person' wishes to upload to.
    :param person: An `IPerson` wishing to upload to an archive.
    :return: A `set` of `IComponent`s that 'person' can upload to.
    """
    permission_set = getUtility(IArchivePermissionSet)
    permissions = permission_set.componentsForUploader(archive, person)
    return set(permission.component for permission in permissions)


def can_upload_to_archive(person, suitesourcepackage, archive=None):
    """Check if 'person' upload 'suitesourcepackage' to 'archive'.

    :param person: An `IPerson` who might be uploading.
    :param suitesourcepackage: An `ISuiteSourcePackage` to be uploaded.
    :param archive: The `IArchive` to upload to. If not provided, defaults
        to the default archive for the source package. (See
        `ISourcePackage.get_default_archive`).
    :return: True if they can, False if they cannot.
    """
    sourcepackage = suitesourcepackage.sourcepackage
    if archive is None:
        archive = sourcepackage.get_default_archive()
    pocket = suitesourcepackage.pocket
    distroseries = sourcepackage.distroseries
    sourcepackagename = sourcepackage.sourcepackagename
    component = sourcepackage.latest_published_component
    # strict_component is True because the source package already exists
    # (otherwise we couldn't have a suitesourcepackage object) and
    # nascentupload passes True as a matter of policy when the package exists.
    reason = check_upload_to_archive(
        person, distroseries, sourcepackagename, archive, component, pocket,
        strict_component=True)
    return reason is None


def check_upload_to_archive(person, distroseries, sourcepackagename, archive,
                            component, pocket, strict_component=True):
    """Check if 'person' upload 'suitesourcepackage' to 'archive'.

    :param person: An `IPerson` who might be uploading.
    :param distroseries: The `IDistroSeries` being uploaded to.
    :param sourcepackagename: The `ISourcePackageName` being uploaded.
    :param archive: The `IArchive` to upload to. If not provided, defaults
        to the default archive for the source package. (See
        `ISourcePackage.get_default_archive`).
    :param component: The `Component` being uploaded to.
    :param pocket: The `PackagePublishingPocket` of 'distroseries' being
        uploaded to.
    :return: The reason for not being able to upload, None otherwise.
    """
    if archive.purpose == ArchivePurpose.PARTNER:
        if pocket not in (
            PackagePublishingPocket.RELEASE,
            PackagePublishingPocket.PROPOSED):
            return InvalidPocketForPartnerArchive()
    elif archive.is_ppa:
        if pocket != PackagePublishingPocket.RELEASE:
            return InvalidPocketForPPA()
    else:
        # Uploads to the partner archive are allowed in any distroseries
        # state.
        # XXX julian 2005-05-29 bug=117557:
        # This is a greasy hack until bug #117557 is fixed.
        if not distroseries.canUploadToPocket(pocket):
            return CannotUploadToPocket(distroseries, pocket)

    return verify_upload(
        person, sourcepackagename, archive, component, distroseries,
        strict_component)


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
                  distroseries, strict_component=True):
    """Can 'person' upload 'sourcepackagename' to 'archive'?

    :param person: The `IPerson` trying to upload to the package. Referred to
        as 'the signer' in upload code.
    :param sourcepackagename: The source package being uploaded. None if the
        package is new.
    :param archive: The `IArchive` being uploaded to.
    :param component: The `IComponent` that the source package belongs to.
    :param distroseries: The upload's target distro series.
    :param strict_component: True if access to the specific component for the
        package is needed to upload to it. If False, then access to any
        package will do.
    :return: CannotUploadToArchive if 'person' cannot upload to the archive,
        None otherwise.
    """
    if not archive.enabled:
        return ArchiveDisabled(archive.displayname)

    # For PPAs...
    if archive.is_ppa:
        if not archive.canUpload(person):
            return CannotUploadToPPA()
        else:
            return None

    # For any other archive...
    ap_set = getUtility(IArchivePermissionSet)

    if sourcepackagename is not None:
        # Check whether user may upload because he holds a permission for
        #   - the given source package directly
        #   - a package set in the correct distro series that includes the
        #     given source package
        source_allowed = archive.canUpload(person, sourcepackagename)
        set_allowed = ap_set.isSourceUploadAllowed(
            archive, sourcepackagename, person, distroseries)
        if source_allowed or set_allowed:
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

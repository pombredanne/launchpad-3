# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Permissions for uploading a package to an archive."""

__metaclass__ = type
__all__ = [
    'CannotUploadToArchive',
    'CannotUploadToPPA',
    'components_valid_for',
    'person_may_edit_branch',
    'verify_upload',
    ]

from zope.component import getUtility

from canonical.launchpad.webapp.authorization import check_permission

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
    ap_set = getUtility(IArchivePermissionSet)
    if sourcepackagename is not None and (
        archive.canUpload(person, sourcepackagename)
        or ap_set.isSourceUploadAllowed(archive, sourcepackagename, person)):
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

def person_may_edit_branch(person, branch):
    """Return True if person may edit branch.

    A person P may be allowed to edit the branch B on the following
    grounds:

      - P is owner of B or a member of the team owning B
      - B is a source package branch (i.e. a branch linked to a
        source package SP in the distro series DS, component C) and
        - P is authorised to upload SP in DS.distribution.main_archive
        - P is authorised to upload to C in DS.distribution.main_archive
        - P is authorised to upload SP via a package set

    :param person: The `IPerson` for which to check edit privileges.
    :param branch: The `IBranch` for which to check edit privileges.
    :return: True if 'person' has edit privileges for 'branch',
             False otherwise.
    """
    def current_component(ds, package):
        releases = ds.getCurrentSourceReleases(
            [package.sourcepackagename])
        return releases.get(package, None)

    result = check_permission('launchpad.Edit', branch)
    # P is owner of B or a member of the team owning B
    if result == True:
        return result

    # Check whether we're dealing with a source package branch and
    # whether person is authorised to upload the respective source
    # package.
    package = branch.sourcepackage
    if package is None:
        # No package .. hmm .. this can't be a source package branch
        # then. Abort.
        return False

    distroseries = branch.distroseries
    if distroseries is None:
        # No distro series? Very fishy .. abort.
        return False

    archive = branch.distroseries.distribution.main_archive
    spn = package.sourcepackagename
    component = current_component(distroseries, package)

    # Is person authorised to upload the source package this branch
    # is targeting?
    result = verify_upload(person, spn, archive, component)
    # verify_upload() indicates that person *is* allowed to upload by
    # returning None.
    return result is None
    

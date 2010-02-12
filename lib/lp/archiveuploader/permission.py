# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Permissions for uploading a package to an archive."""

__metaclass__ = type
__all__ = [
    'CannotUploadToArchive',
    'CannotUploadToPPA',
    ]


class CannotUploadToArchive:
    """A reason for not being able to upload to an archive."""

    _fmt = '%(person)s has no upload rights to %(archive)s.'

    def __init__(self, **args):
        """Construct a `CannotUploadToArchive`."""
        self._message = self._fmt % args

    def __str__(self):
        return self._message


class CannotUploadToPocket:
    """Returned when a pocket is closed for uploads."""

    def __init__(self, distroseries, pocket):
        super(CannotUploadToPocket, self).__init__(
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
        super(NoRightsForComponent, self).__init__(component=component.name)


class InvalidPocketForPPA(CannotUploadToArchive):
    """PPAs only support some pockets."""

    _fmt = "PPA uploads must be for the RELEASE pocket."


class InvalidPocketForPartnerArchive(CannotUploadToArchive):
    """Partner archives only support some pockets."""

    _fmt = "Partner uploads must be for the RELEASE or PROPOSED pocket."




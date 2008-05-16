# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0213

"""ArchivePermission interface."""

__metaclass__ = type

__all__ = [
    'ArchivePermissionType',
    'IArchivePermission',
    'IArchivePermissionSet',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Choice, Datetime

from canonical.launchpad import _
from canonical.lazr import DBEnumeratedType, DBItem


class ArchivePermissionType(DBEnumeratedType):
    """Archive Permission Type.

    The permission being granted, such as upload rights, or queue
    manipulation rights.
    """

    UPLOAD = DBItem(1, """
        Archive Upload Rights

        This permission allows a user to upload.
        """)

    QUEUE_ADMIN = DBItem(2, """
        Queue Administration Rights

        This permission allows a user to administer the distroseries
        upload queue.
        """)


class IArchivePermission(Interface):
    """The interface for `ArchivePermission`."""

    id = Attribute("The archive permission ID.")

    date_created = Datetime(
        title=_('Date Created'), required=False, readonly=False,
        description=_("The timestamp when the permission was created."))

    archive = Attribute("The archive that this permission is for.")

    permission = Choice(
        title=_("The permission type being granted."),
        values=ArchivePermissionType, readonly=False, required=True)

    person = Choice(
        title=_("Person"),
        description=_("The person or team being granted the permission."),
        required=True, vocabulary="ValidPersonOrTeam")

    component = Attribute("The component that this permission is related to.")

    sourcepackagename = Attribute(
        "The source package name that this permission is related to.")


class IArchivePermissionSet(Interface):
    """The interface for `ArchivePermissionSet`."""

    def checkAuthenticated(user, archive, permission, item):
        """The `ArchivePermission` records that authenticate the user.

        :param user: An `IPerson` whom should be checked for authentication.
        :param archive: The context `IArchive` for the permission check.
        :param permission: The `ArchivePermissionType` to check.
        :param item: The context `IComponent` or `ISourcePackageName` for the
            permission check.

        :return: all the `ArchivePermission` records that match the parameters
        supplied.  If none are returned, it means the user is not
        authenticated in that context.
        """

    def uploadersForComponent(archive, component=None):
        """The `ArchivePermission` records for authorised component uploaders.

        :param archive: The context `IArchive` for the permission check.
        :param component: Optional `IComponent`, if specified will only
            return records for uploaders to that component, otherwise
            all components are considered.

        :return: `ArchivePermission` records for all the uploaders who
            are authorised for the supplied component.
        """

    def componentsForUploader(archive, user):
        """The `ArchivePermission` records for the user's upload components.

        :param archive: The context `IArchive` for the permission check.
        :param user: An `IPerson` for whom you want to find out which
            components he has access to.

        :return: `ArchivePermission` records for all the components that
            'user' is allowed to upload to.
        """

    def uploadersForPackage(archive, sourcepackagename):
        """The `ArchivePermission` records for authorised package uploaders.

        :param archive: The context `IArchive` for the permission check.
        :param sourcepackagename: An `ISourcePackageName` or a string
            package name.
        :raises NotFoundError: if the string package name does not exist.

        :return: `ArchivePermission` records for all the uploaders who are
            authorised to upload the named source package.
        """

    def queueAdminsForComponent(archive, component):
        """The `ArchivePermission` records for authorised queue admins.

        :param archive: The context `IArchive` for the permission check.
        :param component: The context `IComponent` for the permission check.

        :return: `ArchivePermission` records for all the users who are allowed
        to administer the distroseries upload queue.
        """

    def componentsForQueueAdmin(archive, user):
        """Return `ArchivePermission`s for the user's queue admin components.

        :param archive: The context `IArchive` for the permission check.
        :param user: An `IPerson` for whom you want to find out which
            components he has access to.

        :return: `ArchivePermission` records for all the components that
            'user' is allowed to administer the queue for.
        """

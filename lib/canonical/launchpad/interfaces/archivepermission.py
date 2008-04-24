# Copyright 2008 Canonical Ltd.  All rights reserved.

"""ArchivePermission interface."""

__metaclass__ = type

__all__ = [
    'ArchivePermissionType',
    'IArchivePermission',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Choice

from canonical.launchpad import _
from canonical.lazr import DBEnumeratedType, DBItem


class ArchivePermissionType(DBEnumeratedType):
    """Archive Permission Type

    The permission being granted, such as upload rights, or queue
    manipulation rights.
    """

    UPLOAD = DBItem(1, """
        Archive Upload Rights

        This permission allows a user to upload.
        """)

    QUEUE_ADMIN = DBItem(2, """
        Queue administration rights

        This permission allows a user to administer the distroseries
        upload queue.
        """)


class IArchivePermission(Interface):
    """ArchivePermission interface."""

    id = Attribute("The archive permission ID.")

    date_created = Attribute("The timestamp when the permission was created.")

    archive = Attribute("The archive that this permission is for.")

    permission = Choice(
        title=_("The permission type being granted."),
        values=ArchivePermissionType, readonly=False, required=True)

    person = Attribute("The person or team being granted the permission.")

    component = Attribute("The component that this permission is related to.")

    sourcepackagename = Attribute(
        "The source package name that this permission is related to.")


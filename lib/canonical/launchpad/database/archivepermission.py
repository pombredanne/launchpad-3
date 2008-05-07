# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Database class for table ArchivePermission."""

__metaclass__ = type

__all__ = [
    'ArchivePermission',
    'ArchivePermissionSet',
    ]

from sqlobject import ForeignKey
from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import (
    ArchivePermissionType, IArchivePermission, IArchivePermissionSet,
    IComponent, ISourcePackageName, ISourcePackageNameSet)


class ArchivePermission(SQLBase):
    """See `IArchivePermission`."""
    implements(IArchivePermission)
    _table = 'ArchivePermission'
    _defaultOrder = 'id'

    date_created = UtcDateTimeCol(
        dbName='date_created', notNull=True, default=UTC_NOW)

    archive = ForeignKey(foreignKey='Archive', dbName='archive', notNull=True)

    permission = EnumCol(
        dbName='permission', unique=False, notNull=True,
        schema=ArchivePermissionType)

    person = ForeignKey(foreignKey='Person', dbName='person', notNull=True)

    component = ForeignKey(
        foreignKey='Component', dbName='component', notNull=False)

    sourcepackagename = ForeignKey(
        foreignKey='SourcePackageName', dbName='sourcepackagename',
        notNull=False)


class ArchivePermissionSet:
    """See `IArchivePermissionSet`."""
    implements(IArchivePermissionSet)

    def checkAuthenticated(self, user, archive, permission, item):
        """See `IArchivePermissionSet`."""
        if IComponent.providedBy(item):
            auth = ArchivePermission.selectBy(
                archive=archive, permission=permission, person=user,
                component=item)
        elif ISourcePackageName.providedBy(item):
            auth = ArchivePermission.selectBy(
                archive=archive, permission=permission, person=user,
                sourcepackagename=item)
        else:
            raise TypeError(
                "'item' is not an IComponent or an ISourcePackageName")

        return auth

    def uploadersForComponent(self, archive, component=None):
        "See `IArchivePermissionSet`."""
        return ArchivePermission.selectBy(
            archive=archive, permission=ArchivePermissionType.UPLOAD,
            component=component)

    def uploadersForPackage(self, archive, sourcepackagename):
        "See `IArchivePermissionSet`."""
        if isinstance(sourcepackagename, basestring):
            sourcepackagename = getUtility(
                ISourcePackageNameSet)[sourcepackagename]
        return ArchivePermission.selectBy(
            archive=archive, permission=ArchivePermissionType.UPLOAD,
            sourcepackagename=sourcepackagename)

    def queueAdminsForComponent(self, archive, component):
        "See `IArchivePermissionSet`."""
        return ArchivePermission.selectBy(
            archive=archive, permission=ArchivePermissionType.QUEUE_ADMIN,
            component=component)

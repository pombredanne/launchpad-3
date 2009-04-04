# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Database class for table ArchivePermission."""

__metaclass__ = type

__all__ = [
    'ArchivePermission',
    'ArchivePermissionSet',
    ]

from sqlobject import ForeignKey
from storm.store import Store
from zope.component import getUtility
from zope.interface import alsoProvides, implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import sqlvalues, SQLBase

from canonical.launchpad.interfaces.archive import ComponentNotFound, SourceNotFound
from canonical.launchpad.interfaces.archivepermission import (
    ArchivePermissionType, IArchivePermission, IArchivePermissionSet,
    IArchiveUploader, IArchiveQueueAdmin)
from canonical.launchpad.interfaces.component import IComponent, IComponentSet
from lp.registry.interfaces.sourcepackagename import (
    ISourcePackageName, ISourcePackageNameSet)
from canonical.launchpad.webapp.interfaces import NotFoundError

from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)


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

    def _init(self, *args, **kw):
        """Provide the right interface for URL traversal."""
        SQLBase._init(self, *args, **kw)

        # Provide the additional marker interface depending on what type
        # of archive this is.  See also the browser:url declarations in
        # zcml/archivepermission.zcml.
        if self.permission == ArchivePermissionType.UPLOAD:
            alsoProvides(self, IArchiveUploader)
        elif self.permission == ArchivePermissionType.QUEUE_ADMIN:
            alsoProvides(self, IArchiveQueueAdmin)
        else:
            raise AssertionError, (
                "Unknown permission type %s" % self.permission)

    @property
    def component_name(self):
        """See `IArchivePermission`"""
        if self.component:
            return self.component.name 
        else:
            return None

    @property
    def source_package_name(self):
        """See `IArchivePermission`"""
        if self.sourcepackagename:
            return self.sourcepackagename.name
        else:
            return None


class ArchivePermissionSet:
    """See `IArchivePermissionSet`."""
    implements(IArchivePermissionSet)

    def checkAuthenticated(self, person, archive, permission, item):
        """See `IArchivePermissionSet`."""
        clauses = ["""
            ArchivePermission.archive = %s AND
            ArchivePermission.permission = %s AND
            EXISTS (SELECT TeamParticipation.person
                    FROM TeamParticipation
                    WHERE TeamParticipation.person = %s AND
                          TeamParticipation.team = ArchivePermission.person)
            """ % sqlvalues(archive, permission, person)
            ]

        prejoins = []

        if IComponent.providedBy(item):
            clauses.append(
                "ArchivePermission.component = %s" % sqlvalues(item))
            prejoins.append("component")
        elif ISourcePackageName.providedBy(item):
            clauses.append(
                "ArchivePermission.sourcepackagename = %s" % sqlvalues(item))
            prejoins.append("sourcepackagename")
        else:
            raise TypeError(
                "'item' is not an IComponent or an ISourcePackageName")

        query = " AND ".join(clauses)
        auth = ArchivePermission.select(
            query, clauseTables=["TeamParticipation"], distinct=True,
            prejoins=prejoins)

        return auth

    def _nameToComponent(self, component):
        """Helper to convert a possible string component to IComponent"""
        try:
            if isinstance(component, basestring):
                component = getUtility(IComponentSet)[component]
            return component
        except NotFoundError, e:
            raise ComponentNotFound(e)

    def _nameToSourcePackageName(self, sourcepackagename):
        """Helper to convert a possible string name to ISourcePackageName."""
        try:
            if isinstance(sourcepackagename, basestring):
                sourcepackagename = getUtility(
                    ISourcePackageNameSet)[sourcepackagename]
            return sourcepackagename
        except NotFoundError, e:
            raise SourceNotFound(e)

    def permissionsForPerson(self, archive, person):
        """See `IArchivePermissionSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(
            ArchivePermission, """
            ArchivePermission.archive = %s AND
            EXISTS (SELECT TeamParticipation.person
                    FROM TeamParticipation
                    WHERE TeamParticipation.person = %s AND
                          TeamParticipation.team = ArchivePermission.person)
            """ % sqlvalues(archive, person))

    def _componentsFor(self, archive, person, permission_type):
        """Helper function to get ArchivePermission objects."""
        return ArchivePermission.select("""
            ArchivePermission.archive = %s AND
            ArchivePermission.permission = %s AND
            ArchivePermission.component IS NOT NULL AND
            EXISTS (SELECT TeamParticipation.person
                    FROM TeamParticipation
                    WHERE TeamParticipation.person = %s AND
                          TeamParticipation.team = ArchivePermission.person)
            """ % sqlvalues(archive, permission_type, person),
            prejoins=["component"])

    def componentsForUploader(self, archive, person):
        """See `IArchivePermissionSet`,"""
        return self._componentsFor(
            archive, person, ArchivePermissionType.UPLOAD)

    def uploadersForComponent(self, archive, component=None):
        "See `IArchivePermissionSet`."""
        clauses = ["""
            ArchivePermission.archive = %s AND
            ArchivePermission.permission = %s
            """ % sqlvalues(archive, ArchivePermissionType.UPLOAD)
            ]

        if component is not None:
            component = self._nameToComponent(component)
            clauses.append(
                "ArchivePermission.component = %s" % sqlvalues(component))
        else:
            clauses.append("ArchivePermission.component IS NOT NULL")

        query = " AND ".join(clauses)
        return ArchivePermission.select(query, prejoins=["component"])

    def packagesForUploader(self, archive, person):
        """See `IArchive`."""
        return ArchivePermission.select("""
            ArchivePermission.archive = %s AND
            ArchivePermission.permission = %s AND
            ArchivePermission.sourcepackagename IS NOT NULL AND
            EXISTS (SELECT TeamParticipation.person
                    FROM TeamParticipation
                    WHERE TeamParticipation.person = %s AND
                    TeamParticipation.team = ArchivePermission.person)
            """ % sqlvalues(archive, ArchivePermissionType.UPLOAD, person),
            prejoins=["sourcepackagename"])

    def uploadersForPackage(self, archive, sourcepackagename):
        "See `IArchivePermissionSet`."""
        sourcepackagename = self._nameToSourcePackageName(sourcepackagename)
        results = ArchivePermission.selectBy(
            archive=archive, permission=ArchivePermissionType.UPLOAD,
            sourcepackagename=sourcepackagename)
        return results.prejoin(["sourcepackagename"])

    def queueAdminsForComponent(self, archive, component):
        "See `IArchivePermissionSet`."""
        component = self._nameToComponent(component)
        results = ArchivePermission.selectBy(
            archive=archive, permission=ArchivePermissionType.QUEUE_ADMIN,
            component=component)
        return results.prejoin(["component"])

    def componentsForQueueAdmin(self, archive, person):
        """See `IArchivePermissionSet`."""
        return self._componentsFor(
            archive, person, ArchivePermissionType.QUEUE_ADMIN)

    def newPackageUploader(self, archive, person, sourcepackagename):
        """See `IArchivePermissionSet`."""
        sourcepackagename = self._nameToSourcePackageName(sourcepackagename)
        existing = self.checkAuthenticated(
            person, archive, ArchivePermissionType.UPLOAD, sourcepackagename)
        if existing.count() != 0:
            return existing[0]
        return ArchivePermission(
            archive=archive, person=person,
            sourcepackagename=sourcepackagename,
            permission=ArchivePermissionType.UPLOAD)

    def newComponentUploader(self, archive, person, component):
        """See `IArchivePermissionSet`."""
        component = self._nameToComponent(component)
        existing = self.checkAuthenticated(
            person, archive, ArchivePermissionType.UPLOAD, component)
        if existing.count() != 0:
            return existing[0]
        return ArchivePermission(
            archive=archive, person=person, component=component,
            permission=ArchivePermissionType.UPLOAD)

    def newQueueAdmin(self, archive, person, component):
        """See `IArchivePermissionSet`."""
        component = self._nameToComponent(component)
        existing = self.checkAuthenticated(
            person, archive, ArchivePermissionType.QUEUE_ADMIN, component)
        if existing.count() != 0:
            return existing[0]
        return ArchivePermission(
            archive=archive, person=person, component=component,
            permission=ArchivePermissionType.QUEUE_ADMIN)

    def deletePackageUploader(self, archive, person, sourcepackagename):
        """See `IArchivePermissionSet`."""
        sourcepackagename = self._nameToSourcePackageName(sourcepackagename)
        permission = ArchivePermission.selectOneBy(
            archive=archive, person=person,
            sourcepackagename=sourcepackagename,
            permission=ArchivePermissionType.UPLOAD)
        Store.of(permission).remove(permission)

    def deleteComponentUploader(self, archive, person, component):
        """See `IArchivePermissionSet`."""
        component = self._nameToComponent(component)
        permission = ArchivePermission.selectOneBy(
            archive=archive, person=person, component=component,
            permission=ArchivePermissionType.UPLOAD)
        Store.of(permission).remove(permission)

    def deleteQueueAdmin(self, archive, person, component):
        """See `IArchivePermissionSet`."""
        component = self._nameToComponent(component)
        permission = ArchivePermission.selectOneBy(
            archive=archive, person=person, component=component,
            permission=ArchivePermissionType.QUEUE_ADMIN)
        Store.of(permission).remove(permission)

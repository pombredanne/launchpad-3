# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Database class for table ArchivePermission."""

__metaclass__ = type

__all__ = [
    'ArchivePermission',
    'ArchivePermissionSet',
    ]

from sqlobject import BoolCol, ForeignKey
from storm.expr import In, SQL
from storm.locals import Int, Reference
from storm.store import Store
from zope.component import getUtility
from zope.interface import alsoProvides, implements

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import sqlvalues, SQLBase

from canonical.launchpad.database.packageset import Packageset
from canonical.launchpad.interfaces.archive import (
    ComponentNotFound, SourceNotFound)
from canonical.launchpad.interfaces.archivepermission import (
    ArchivePermissionType, IArchivePermission, IArchivePermissionSet,
    IArchiveUploader, IArchiveQueueAdmin)
from canonical.launchpad.interfaces.component import IComponent, IComponentSet
from canonical.launchpad.interfaces.lpstorm import IMasterStore, IStore
from canonical.launchpad.interfaces.packageset import IPackageset
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.sourcepackagename import (
    ISourcePackageName, ISourcePackageNameSet)
from canonical.launchpad.webapp.interfaces import NotFoundError

from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)


def _extract_type_name(value):
    """Extract the type name of the given value."""
    return str(type(value)).split("'")[-2]


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

    packageset_id = Int(name='packageset', allow_none=True)
    packageset = Reference(packageset_id, 'Packageset.id')

    explicit = BoolCol(dbName='explicit', notNull=True, default=False)

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

    @property
    def package_set_name(self):
        """See `IArchivePermission`"""
        if self.packageset:
            return self.packageset.name
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

    def _nameToPackageset(self, packageset):
        """Helper to convert a possible string name to IPackageset."""
        if isinstance(packageset, basestring):
            name = packageset
            packageset = Store.of(self).find(Packageset, name=name).one()
            if packageset is not None:
                return packageset
            else:
                raise NotFoundError("No such package set '%s'" % name)
        elif IPackageset.providedBy(packageset):
            return packageset
        else:
            raise ValueError(
                'Not a package set: %s' % _extract_type_name(packageset))

    def packagesetsForUploader(self, person):
        """See `IArchivePermissionSet`."""
        store = IStore(ArchivePermission)
        query = '''
            SELECT ap.id
            FROM archivepermission ap, teamparticipation tp
            WHERE
                (ap.person = ? OR (ap.person = tp.team AND tp.person = ?))
                AND ap.packageset IS NOT NULL
        '''
        query = SQL(query, (person.id, person.id))
        return store.find(ArchivePermission, In(ArchivePermission.id, query))

    def uploadersForPackageset(self, packageset, direct_permissions=True):
        """See `IArchivePermissionSet`."""
        packageset = self._nameToPackageset(packageset)
        store = IStore(ArchivePermission)
        if direct_permissions == True:
            query = '''
                SELECT ap.id FROM archivepermission ap WHERE ap.packageset = ?
            '''
        else:
            query = '''
                SELECT ap.id
                FROM archivepermission ap, flatpackagesetinclusion fpsi
                WHERE fpsi.child = ? AND ap.packageset = fpsi.parent
            '''
        query = SQL(query, (packageset.id,))
        return store.find(ArchivePermission, In(ArchivePermission.id, query))

    def newPackagesetUploader(self, person, packageset, explicit=False):
        """See `IArchivePermissionSet`."""
        packageset = self._nameToPackageset(packageset)
        store = IMasterStore(ArchivePermission)

        # First see whether we have a matching permission in the database
        # already.
        query = '''
            SELECT ap.id
            FROM archivepermission ap, teamparticipation tp
            WHERE
                (ap.person = ? OR (ap.person = tp.team AND tp.person = ?))
                AND ap.packageset = ?
        '''
        query = SQL(query, (person.id, person.id, packageset.id))
        permissions = list(
            store.find(ArchivePermission, In(ArchivePermission.id, query)))
        if len(permissions) > 0:
            # Found permissions in the database, does the 'explicit' flag
            # have the requested value?
            conflicting = [permission for permission in permissions
                           if permission.explicit != explicit]
            if len(conflicting) > 0:
                # At least one permission with conflicting 'explicit' flag
                # value exists already.
                cperm = conflicting[0]
                raise ValueError(
                    "Permission for package set '%s' already exists for %s "
                    "but with a different 'explicit' flag value (%s)." %
                    (packageset.name, cperm.person.name, cperm.explicit))
            else:
                # No conflicts, does the requested permission exist already?
                existing = [permission for permission in permissions
                            if (permission.explicit == explicit and
                                permission.person == person and
                                permission.packageset == packageset)]
                assert len(existing) <= 1, (
                    "Too many permissions for %s and %s" %
                    (person.name, packageset.name))
                if len(existing) == 1:
                    # The existing permission matches, just return it.
                    return existing[0]

        # The requested permission does not exist yet. Insert it into the
        # database.
        permission = ArchivePermission(
            archive=getUtility(IDistributionSet)['ubuntu'].main_archive,
            person=person, packageset=packageset,
            permission=ArchivePermissionType.UPLOAD, explicit=explicit)
        store.add(permission)

        return permission

    def deletePackagesetUploader(self, person, packageset, explicit=False):
        """See `IArchivePermissionSet`."""
        packageset = self._nameToPackageset(packageset)
        store = IMasterStore(ArchivePermission)

        # Do we have the permission the user wants removed in the database?
        permission = store.find(
            ArchivePermission, person=person, packageset=packageset,
            permission=ArchivePermissionType.UPLOAD, explicit=explicit).one()

        if permission is not None:
            # Permission found, remove it!
            store.remove(permission)

    def packagesetsForSourceUploader(self, sourcepackagename, person):
        """See `IArchivePermissionSet`."""
        sourcepackagename = self._nameToSourcePackageName(sourcepackagename)
        store = IStore(ArchivePermission)
        query = '''
            SELECT ap.id
            FROM
                archivepermission ap, teamparticipation tp,
                packagesetsources pss, flatpackagesetinclusion fpsi
            WHERE
                (ap.person = ? OR (ap.person = tp.team AND tp.person = ?))
                AND ap.packageset = fpsi.parent
                AND pss.packageset = fpsi.child
                AND pss.sourcepackagename = ?
        '''
        query = SQL(query, (person.id, person.id, sourcepackagename.id))
        return store.find(ArchivePermission, In(ArchivePermission.id, query))

    def isSourceUploadAllowed(self, sourcepackagename, person):
        """See `IArchivePermissionSet`."""
        sourcepackagename = self._nameToSourcePackageName(sourcepackagename)
        store = IStore(ArchivePermission)

        # Put together the parameters for the query that follows.
        permission = ArchivePermissionType.UPLOAD
        query_params = (
            (sourcepackagename.id,)*2 + (person.id,)*2 + (permission,) + 
            (sourcepackagename.id,)   + (person.id,)*2 + (permission,))

        query = '''
        SELECT CASE
          WHEN (
            SELECT COUNT(ap.id)
            FROM packagesetsources pss, archivepermission ap
            WHERE
              pss.sourcepackagename = %s AND pss.packageset = ap.packageset
              AND ap.explicit = TRUE) > 0
          THEN (
            SELECT COUNT(ap.id)
            FROM
              packagesetsources pss, archivepermission ap,
              teamparticipation tp
            WHERE
              pss.sourcepackagename = %s
              AND (ap.person = %s OR (ap.person = tp.team AND tp.person = %s))
              AND pss.packageset = ap.packageset AND ap.explicit = TRUE
              AND ap.permission = %s)
          ELSE (
            SELECT COUNT(ap.id)
            FROM
              packagesetsources pss, archivepermission ap,
              teamparticipation tp, flatpackagesetinclusion fpsi
            WHERE
              pss.sourcepackagename = %s
              AND (ap.person = %s OR (ap.person = tp.team AND tp.person = %s))
              AND pss.packageset = fpsi.child AND fpsi.parent = ap.packageset
              AND ap.permission = %s)
        END AS number_of_permitted_package_sets;

        ''' % sqlvalues(*query_params)
        return store.execute(query).get_one()[0] > 0

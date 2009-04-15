# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Packageset', 'PackagesetSet']

import pytz

from storm.expr import In, SQL
from storm.locals import DateTime, Int, Reference, Storm, Unicode

from zope.component import getUtility
from zope.interface import implements

from lp.registry.model.sourcepackagename import SourcePackageName
from canonical.launchpad.interfaces.packageset import (
    IPackageset, IPackagesetSet)
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)


class Packageset(Storm):
    """See `IPackageset`."""
    implements(IPackageset)
    __storm_table__ = 'Packageset'
    id = Int(primary=True)

    date_created = DateTime(
        name='date_created', allow_none=False, tzinfo=pytz.UTC)

    owner_id = Int(name='owner', allow_none=False)
    owner = Reference(owner_id, 'Person.id')

    name = Unicode(name='name', allow_none=False)
    description = Unicode(name='description', allow_none=False)

    def addSourcePackageNames(self, spns):
        """See `IPackageset`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        query = '''
            INSERT INTO packagesetsources(packageset, sourcepackagename) (
                SELECT ? AS packageset, spn.id AS sourcepackagename
                FROM sourcepackagename spn WHERE spn.id IN (%s)
                EXCEPT
                SELECT packageset, sourcepackagename FROM packagesetsources
                WHERE packageset = ?)
        ''' % ','.join(str(spn.id) for spn in spns)
        store.execute(query, (self.id, self.id), noresult=True)

    def removeSourcePackageNames(self, spns):
        """See `IPackageset`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        query = '''
            DELETE FROM packagesetsources
            WHERE packageset = ? AND sourcepackagename IN (%s)
        ''' % ','.join(str(spn.id) for spn in spns)
        store.execute(query, (self.id,), noresult=True)

    def getDirectSourcePackageNames(self):
        """See `IPackageset`."""
        spn_query = '''
            SELECT pss.sourcepackagename FROM packagesetsources pss
            WHERE pss.packageset = ?
        '''
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        spns = SQL(spn_query, (self.id,))
        return store.find(SourcePackageName, In(SourcePackageName.id, spns))

    def getSourcePackageNames(self):
        """See `IPackageset`."""
        spn_query = '''
            SELECT pss.sourcepackagename
            FROM packagesetsources pss, flatpackagesetinclusion fpsi
            WHERE pss.packageset = fpsi.child AND fpsi.parent = ?
        '''
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        spns = SQL(spn_query, (self.id,))
        return store.find(SourcePackageName, In(SourcePackageName.id, spns))

    def addDirectSuccessor(self, package_set):
        """See `IPackageset`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        adsq = '''
            INSERT INTO packagesetinclusion(parent, child) (
                SELECT ? AS parent, ? AS child
                EXCEPT
                SELECT parent, child FROM packagesetinclusion
                WHERE parent = ?)
        '''
        store.execute(adsq, (self.id, package_set.id, self.id), noresult=True)

    def removeDirectSuccessor(self, package_set):
        """See `IPackageset`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        rdsq = '''
            DELETE FROM packagesetinclusion WHERE parent = ? AND child = ?
        '''
        store.execute(rdsq, (self.id, package_set.id), noresult=True)

    def getPredecessors(self):
        """See `IPackageset`."""
        # The very last clause in the query is necessary because each
        # package set is also a predecessor of itself in the flattened
        # hierarchy.
        query = '''
            SELECT fpsi.parent FROM flatpackagesetinclusion fpsi
            WHERE fpsi.child = ? AND fpsi.parent != ?
        '''
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        predecessors = SQL(query, (self.id, self.id))
        return store.find(Packageset, In(Packageset.id, predecessors))

    def getDirectPredecessors(self):
        """See `IPackageset`."""
        query = '''
            SELECT psi.parent FROM packagesetinclusion psi WHERE psi.child = ?
        '''
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        predecessors = SQL(query, (self.id, ))
        return store.find(Packageset, In(Packageset.id, predecessors))

    def getSuccessors(self):
        """See `IPackageset`."""
        # The very last clause in the query is necessary because each
        # package set is also a successor of itself in the flattened
        # hierarchy.
        query = '''
            SELECT fpsi.child FROM flatpackagesetinclusion fpsi
            WHERE fpsi.parent = ? AND fpsi.child != ?
        '''
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        successors = SQL(query, (self.id, self.id))
        return store.find(Packageset, In(Packageset.id, successors))

    def getDirectSuccessors(self):
        """See `IPackageset`."""
        query = '''
            SELECT psi.child FROM packagesetinclusion psi WHERE psi.parent = ?
        '''
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        successors = SQL(query, (self.id, ))
        return store.find(Packageset, In(Packageset.id, successors))


class PackagesetSet:
    """See `IPackagesetSet`."""
    implements(IPackagesetSet)

    def new(self, name, description, owner):
        """See `IPackagesetSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        packageset = Packageset()
        packageset.name = name
        packageset.description = description
        packageset.owner = owner
        store.add(packageset)
        return packageset

    def getByName(self, name):
        """See `IPackagesetSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(Packageset, Packageset.name == name).one()

    def getByOwner(self, owner):
        """See `IPackagesetSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(Packageset, Packageset.owner == owner)

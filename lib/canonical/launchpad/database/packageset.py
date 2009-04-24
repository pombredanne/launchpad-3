# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Packageset', 'PackagesetSet']

import pytz

from storm.expr import In, SQL
from storm.locals import DateTime, Int, Reference, Storm, Unicode

from zope.component import getUtility
from zope.interface import implements

from lp.registry.interfaces.sourcepackagename import (
    ISourcePackageName, ISourcePackageNameSet)
from lp.registry.model.sourcepackagename import SourcePackageName

from canonical.launchpad.interfaces import IMasterStore, IStore
from canonical.launchpad.interfaces.packageset import (
    IPackageset, IPackagesetSet)


def _order_result_set(result_set):
    """Default order for package set and source package name result sets."""
    return result_set.order_by('name')

def _extract_type_name(value):
    """Extract the type name of the given value."""
    return str(type(value)).split("'")[-2]


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

    def add(self, data):
        """See `IPackageset`."""
        handlers = (
            (ISourcePackageName, self._addSourcePackageNames),
            (IPackageset, self._addDirectSuccessors))
        self._add_or_remove(data, handlers)

    def remove(self, data):
        """See `IPackageset`."""
        handlers = (
            (ISourcePackageName, self._removeSourcePackageNames),
            (IPackageset, self._removeDirectSuccessors))
        self._add_or_remove(data, handlers)

    def _add_or_remove(self, data, handlers):
        """Add or remove source package names or package sets from this one.

        :param data: an iterable with `ISourcePackageName` XOR `IPackageset`
            instances
        :param handlers: a 2-tuple Sequence where the first member is the
            interface a datum should implement and the second is the handler
            to invoke in that case respectively.
        """
        store = IMasterStore(Packageset)
        if not isinstance(data, (list, tuple)):
            data = list(data)
        count = len(data)
        for iface, handler in handlers:
            iface_data = [datum for datum in data if iface.providedBy(datum)]
            if len(iface_data) > 0:
                handler(iface_data, store)
                count -= len(iface_data)
        if count != 0:
            raise AssertionError("Not all data was handled.")

    def _addSourcePackageNames(self, spns, store):
        """Add the given source package names to the package set.

        Souce package names already *directly* associated are ignored."""
        query = '''
            INSERT INTO packagesetsources(packageset, sourcepackagename) (
                SELECT ? AS packageset, spn.id AS sourcepackagename
                FROM sourcepackagename spn WHERE spn.id IN (%s)
                EXCEPT
                SELECT packageset, sourcepackagename FROM packagesetsources
                WHERE packageset = ?)
        ''' % ','.join(str(spn.id) for spn in spns)
        store.execute(query, (self.id, self.id), noresult=True)

    def _removeSourcePackageNames(self, spns, store):
        """Remove the given source package names from the package set."""
        query = '''
            DELETE FROM packagesetsources
            WHERE packageset = ? AND sourcepackagename IN (%s)
        ''' % ','.join(str(spn.id) for spn in spns)
        store.execute(query, (self.id,), noresult=True)

    def _addDirectSuccessors(self, packagesets, store):
        """Add the given package sets as directly included subsets."""
        adsq = '''
            INSERT INTO packagesetinclusion(parent, child) (
                SELECT ? AS parent, cps.id AS child
                FROM packageset cps WHERE cps.id IN (%s)
                EXCEPT
                SELECT parent, child FROM packagesetinclusion
                WHERE parent = ?)
        ''' % ','.join(str(packageset.id) for packageset in packagesets)
        store.execute(adsq, (self.id, self.id), noresult=True)

    def _removeDirectSuccessors(self, packagesets, store):
        """Remove the given package sets as directly included subsets."""
        rdsq = '''
            DELETE FROM packagesetinclusion
            WHERE parent = ? AND child IN (%s)
        ''' % ','.join(str(packageset.id) for packageset in packagesets)
        store.execute(rdsq, (self.id,), noresult=True)

    def sourcesIncluded(self, direct_inclusion=False):
        """See `IPackageset`."""
        if direct_inclusion == False:
            spn_query = '''
                SELECT pss.sourcepackagename
                FROM packagesetsources pss, flatpackagesetinclusion fpsi
                WHERE pss.packageset = fpsi.child AND fpsi.parent = ?
            '''
        else:
            spn_query = '''
                SELECT pss.sourcepackagename FROM packagesetsources pss
                WHERE pss.packageset = ?
            '''
        store = IStore(Packageset)
        spns = SQL(spn_query, (self.id,))
        rset = store.find(SourcePackageName, In(SourcePackageName.id, spns))
        return _order_result_set(rset)

    def getSourcesIncluded(self, direct_inclusion=False):
        """See `IPackageset`."""
        rset = self.sourcesIncluded(direct_inclusion)
        return rset.values(SourcePackageName.name)

    def setsIncludedBy(self, direct_inclusion=False):
        """See `IPackageset`."""
        if direct_inclusion == False:
            # The very last clause in the query is necessary because each
            # package set is also a predecessor of itself in the flattened
            # hierarchy.
            query = '''
                SELECT fpsi.parent FROM flatpackagesetinclusion fpsi
                WHERE fpsi.child = ? AND fpsi.parent != ?
            '''
            params = (self.id, self.id)
        else:
            query = '''
                SELECT psi.parent FROM packagesetinclusion psi
                WHERE psi.child = ?
            '''
            params = (self.id,)
        store = IStore(Packageset)
        predecessors = SQL(query, params)
        rset = store.find(Packageset, In(Packageset.id, predecessors))
        return _order_result_set(rset)

    def setsIncluded(self, direct_inclusion=False):
        """See `IPackageset`."""
        if direct_inclusion == False:
            # The very last clause in the query is necessary because each
            # package set is also a successor of itself in the flattened
            # hierarchy.
            query = '''
                SELECT fpsi.child FROM flatpackagesetinclusion fpsi
                WHERE fpsi.parent = ? AND fpsi.child != ?
            '''
            params = (self.id, self.id)
        else:
            query = '''
                SELECT psi.child FROM packagesetinclusion psi
                WHERE psi.parent = ?
            '''
            params = (self.id,)
        store = IStore(Packageset)
        successors = SQL(query, params)
        rset = store.find(Packageset, In(Packageset.id, successors))
        return _order_result_set(rset)

    def sourcesSharedBy(self, other_package_set, direct_inclusion=False):
        """See `IPackageset`."""
        if direct_inclusion == False:
            query = '''
                SELECT pss_this.sourcepackagename
                FROM
                    packagesetsources pss_this, packagesetsources pss_other,
                    flatpackagesetinclusion fpsi_this,
                    flatpackagesetinclusion fpsi_other
                WHERE pss_this.sourcepackagename = pss_other.sourcepackagename
                    AND pss_this.packageset = fpsi_this.child
                    AND pss_other.packageset = fpsi_other.child
                    AND fpsi_this.parent = ?  AND fpsi_other.parent = ?
            '''
        else:
            query = '''
                SELECT pss_this.sourcepackagename
                FROM packagesetsources pss_this, packagesetsources pss_other
                WHERE pss_this.sourcepackagename = pss_other.sourcepackagename
                    AND pss_this.packageset = ? AND pss_other.packageset = ?
            '''
        store = IStore(Packageset)
        spns = SQL(query, (self.id, other_package_set.id))
        rset = store.find(SourcePackageName, In(SourcePackageName.id, spns))
        return _order_result_set(rset)

    def getSourcesSharedBy(self, other_package_set, direct_inclusion=False):
        """See `IPackageset`."""
        rset = self.sourcesSharedBy(other_package_set, direct_inclusion)
        return rset.values(SourcePackageName.name)

    def sourcesNotSharedBy(self, other_package_set, direct_inclusion=False):
        """See `IPackageset`."""
        if direct_inclusion == False:
            query = '''
                SELECT pss_this.sourcepackagename
                FROM packagesetsources pss_this, 
                    flatpackagesetinclusion fpsi_this
                WHERE pss_this.packageset = fpsi_this.child
                    AND fpsi_this.parent = ?
                EXCEPT
                SELECT pss_other.sourcepackagename
                FROM packagesetsources pss_other, 
                    flatpackagesetinclusion fpsi_other
                WHERE pss_other.packageset = fpsi_other.child
                    AND fpsi_other.parent = ?
            '''
        else:
            query = '''
                SELECT pss_this.sourcepackagename
                FROM packagesetsources pss_this WHERE pss_this.packageset = ?
                EXCEPT
                SELECT pss_other.sourcepackagename
                FROM packagesetsources pss_other
                WHERE pss_other.packageset = ?
            '''
        store = IStore(Packageset)
        spns = SQL(query, (self.id, other_package_set.id))
        rset = store.find(SourcePackageName, In(SourcePackageName.id, spns))
        return _order_result_set(rset)

    def getSourcesNotSharedBy(
        self, other_package_set, direct_inclusion=False):
        """See `IPackageset`."""
        rset = self.sourcesNotSharedBy(other_package_set, direct_inclusion)
        return rset.values(SourcePackageName.name)

    def _api_add_or_remove(self, clauses, handler):
        """Look up the data to be added/removed and call the handler."""
        store = IMasterStore(Packageset)
        data = list(store.find(*clauses))
        if len(data) > 0:
            handler(data, store)

    def addSources(self, names):
        """See `IPackageset`."""
        clauses = (SourcePackageName, In(SourcePackageName.name, names))
        self._api_add_or_remove(clauses, self._addSourcePackageNames)

    def removeSources(self, names):
        """See `IPackageset`."""
        clauses = (SourcePackageName, In(SourcePackageName.name, names))
        self._api_add_or_remove(clauses, self._removeSourcePackageNames)

    def addSubsets(self, names):
        """See `IPackageset`."""
        clauses = (Packageset, In(Packageset.name, names))
        self._api_add_or_remove(clauses, self._addDirectSuccessors)

    def removeSubsets(self, names):
        """See `IPackageset`."""
        clauses = (Packageset, In(Packageset.name, names))
        self._api_add_or_remove(clauses, self._removeDirectSuccessors)


class PackagesetSet:
    """See `IPackagesetSet`."""
    implements(IPackagesetSet)

    def new(self, name, description, owner):
        """See `IPackagesetSet`."""
        store = IMasterStore(Packageset)
        packageset = Packageset()
        packageset.name = name
        packageset.description = description
        packageset.owner = owner
        store.add(packageset)
        return packageset

    def getByName(self, name):
        """See `IPackagesetSet`."""
        store = IStore(Packageset)
        return store.find(Packageset, Packageset.name == name).one()

    def getByOwner(self, owner):
        """See `IPackagesetSet`."""
        store = IStore(Packageset)
        rset = store.find(Packageset, Packageset.owner == owner)
        return _order_result_set(rset)

    def _nameToSourcePackageName(self, spn):
        """Helper to convert a possible string name to ISourcePackageName."""
        if isinstance(spn, basestring):
            spn = getUtility(ISourcePackageNameSet)[spn]
        return spn

    def setsIncludingSource(self, sourcepackagename, direct_inclusion=False):
        """See `IPackagesetSet`."""
        sourcepackagename = self._nameToSourcePackageName(sourcepackagename)

        if direct_inclusion == False:
            query = '''
                SELECT fpsi.parent
                FROM packagesetsources pss, flatpackagesetinclusion fpsi
                WHERE pss.sourcepackagename = ?
                AND pss.packageset = fpsi.child
            '''
        else:
            query = '''
                SELECT pss.packageset FROM packagesetsources pss
                WHERE pss.sourcepackagename = ?
            '''
        store = IStore(Packageset)
        psets = SQL(query, (sourcepackagename.id,))
        rset = store.find(Packageset, In(Packageset.id, psets))
        return _order_result_set(rset)

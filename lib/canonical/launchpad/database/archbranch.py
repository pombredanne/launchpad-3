# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Branch', 'CategoryMapper', 'BranchMapper', 'VersionMapper']

from canonical.database.sqlbase import quote, SQLBase, sqlvalues
from sqlobject import StringCol, ForeignKey, MultipleJoin

from canonical.launchpad.interfaces import \
    ArchiveNotRegistered, VersionNotRegistered, VersionAlreadyRegistered, \
    BranchAlreadyRegistered, CategoryAlreadyRegistered

from zope.interface import implements
from canonical.launchpad.interfaces import IBranch

from canonical.launchpad.database.archarchive import \
        ArchiveMapper, ArchNamespace, ArchArchive

import pybaz


class Branch(SQLBase):
    """An ordered revision sequence in arch"""

    implements(IBranch)

    _table = 'Branch'
    archnamespace = ForeignKey(foreignKey='ArchNamespace',
        dbName='archnamespace', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    owner = ForeignKey(foreignKey='Person', dbName='owner',
                       default=None)
    product = ForeignKey(foreignKey='Product', dbName='product', default=None)
    changesets = MultipleJoin('Changeset', joinColumn='branch')
    subjectRelations = MultipleJoin('BranchRelationship', joinColumn='subject')
    objectRelations = MultipleJoin('BranchRelationship', joinColumn='object')

    def getPackageName(self):
        """See IBranch."""
        packagename = self.archnamespace.archive.name
        if self.archnamespace.category:
            packagename += '/' + self.archnamespace.category
            if self.archnamespace.branch:
                packagename += '--' + self.archnamespace.branch
                if self.archnamespace.version:
                    packagename += '--' + self.archnamespace.version
        return packagename

    def _get_repository(self):
        repository = self.archive.name
        if self.category:
            repository += '/' + self.category
            if self.branch:
                repository += '--' + self.branch
                if self.version:
                    repository += '--' + self.version
        return repository

    def createRelationship(self, branch, relationship):
        from canonical.launchpad.database import BranchRelationship
        BranchRelationship(subject=self, object=branch, label=relationship)

    def getRelations(self):
        return tuple(self.subjectRelations) + tuple(self.objectRelations)


class CategoryMapper:
    """Map categories to and from the database."""
    def findByName(self, name):
        count = Category.select('category = ' + quote(name)).count()
        from canonical.arch import broker
        if count == 0:
            return broker.MissingCategory(name)
        if count == 1:
            return broker.Category(name)
        else:
            raise RuntimeError, "Name %r found %d results" % (name, count)

    def insert(self, category):
        """Insert a category into the database."""
        if self.exists(category):
            raise CategoryAlreadyRegistered(category.nonarch)
        ArchNamespace(
            archive=ArchiveMapper()._getId(category.archive),
            category=category.nonarch,
            visible=True,
            )

    def update(self, category):
        pass

    def exists(self, category):
        try:
            id = ArchiveMapper()._getId(category.archive)
        except ArchiveNotRegistered:
            return False
        where = ("archarchive = %s AND category = %s"
                 % sqlvalues(id, category.nonarch))
        return bool(ArchNamespace.select(where).count())

class BranchMapper:
    """Map branch to and from the database"""
    def findByName(self, name):
        count = Branch.select('branch = ' + quote(name)).count()
        from canonical.arch import broker
        if count == 0:
            return broker.MissingBranch(name)
        if count == 1:
            return broker.Branch(name)
        else:
            raise RuntimeError, "Name %r found %d results" % (name, count)

    def insert(self, branch):
        """insert a branch into the database"""
        if self.exists(branch):
            raise BranchAlreadyRegistered(branch.fullname)
        archive_id = ArchiveMapper()._getId(branch.category.archive)
        ArchNamespace(
            archive=archive_id,
            category=branch.category.name,
            branch=branch.name,
            visible=True,
            )

        #ArchNamespace._connection.query(
        #    "DELETE FROM ArchNamespace "
        #    "WHERE archarchive = %s AND category = %s AND branch IS NULL"
        #    % sqlvalues(archive_id, branch.category.name))
        #)
        query = (
            "archarchive = %s AND category = %s AND branch IS NULL"
            % sqlvalues(archive_id, branch.category.name)
            )
        for an in ArchNamespace.select(query):
            #print 'deleting %r (%d) from BM.insert' % (an, an.id)
            an.destroySelf()

    def exists(self, branch):
        id = ArchiveMapper()._getId(branch.category.archive)
        where = ("archarchive = %s AND category = %s AND branch = %s"
                 % sqlvalues(id, branch.category.name, branch.name))
        return bool(ArchNamespace.select(where).count())

class VersionMapper:
    """Map versions to and from the database"""
    def findByName(self, name):
        #print name
        parser = pybaz.NameParser(name)
        archive = ArchArchive.selectOne(
            'name = ' + quote(parser.get_archive()))
        if archive is None:
            return broker.MissingVersion(name)
        id = archive.id
        version = ArchNamespace.selectOneBy(
            archarchiveID=id, category=parser.get_category(),
            branch=parser.get_branch(), version=parser.get_version()
            )
        from canonical.arch import broker
        if version is None:
            return broker.MissingVersion(name)
        else:
            # migration code to allow access to the real Version 
            # and yes, this should be tidied - by moving all to native
            # sqlobject.
            result = Branch.selectOneBy(archnamespaceID=version.id)
            if result is None:
                raise VersionNotRegistered(version.fullname)
            return result

    def insert(self, version):
        """insert a version into the database"""
        if self.exists(version):
            raise VersionAlreadyRegistered(version.fullname)
        archive_id = ArchiveMapper()._getId(version.branch.category.archive)
        namespace=ArchNamespace(
            archive=archive_id,
            category=version.branch.category.name,
            branch=version.branch.name,
            version=version.name,
            visible=True,
            )
        result = Branch(archnamespace=namespace.id, title='', description='')

        #ArchNamespace._connection.query(
        #    "DELETE FROM ArchNamespace "
        #    "WHERE archarchive = %s AND category = %s AND branch = %s "
        #    "AND version IS NULL"
        #    % sqlvalues(archive_id, version.branch.category.name,
        #                version.branch.name))
        #)
        query = (
            "archarchive = %s AND category = %s AND branch = %s "
            "AND version IS NULL"
            % sqlvalues(archive_id, version.branch.category.name,
                        version.branch.name))
        for an in ArchNamespace.select(query):
            #print 'deleting %r (%d) from VM.insert' % (an, an.id)
            an.destroySelf()
        return result

    def findVersionQuery(self, version):
        id = ArchiveMapper()._getId(version.branch.category.archive)
        return ("archarchive = %s AND category = %s AND branch = %s "
                 "AND version = %s" 
                 % sqlvalues(id, version.branch.category.nonarch,
                             version.branch.name, version.name))

    def exists(self, version):
        return bool(
            ArchNamespace.select(self.findVersionQuery(version)).count())

    def _getId(self, version):
        result = ArchNamespace.selectOne(self.findVersionQuery(version))
        if result is None:
            raise VersionNotRegistered(version.fullname)
        else:
            return result.id

    def _getDBBranch(self, version):
        id = self._getId(version)
        result = Branch.selectOneBy(archnamespaceID=self._getId(version))
        if result is None:
            raise VersionNotRegistered(version.fullname)
        return result

    def _getDBBranchId(self, version):
        return self._getDBBranch(version).id


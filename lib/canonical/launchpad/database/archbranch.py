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
        parser = pybaz.NameParser(name)
        archive = ArchArchive.selectOne(
            'name = ' + quote(parser.get_archive()))
        if archive is None:
            return broker.MissingVersion(name)
        id = archive.id
        version = ArchNamespace.selectOneBy(
            archiveID=id, category=parser.get_category(),
            branch=parser.get_branch(), version=parser.get_version()
            )
        from canonical.arch import broker
        if version is None:
            return broker.MissingVersion(name)
        else:
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

    def exists(self, version):
        try:
            unused = self._getId(version)
            return True
        except VersionNotRegistered:
            return False

    def _getId(self, version):
        archiveID = ArchiveMapper()._getId(version.branch.category.archive)
        result = ArchNamespace.selectOneBy(
            archiveID = archiveID,
            category = version.branch.category.nonarch,
            branch = version.branch.name,
            version = version.name)
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


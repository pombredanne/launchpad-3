from canonical.database.sqlbase import quote, SQLBase
from sqlobject import StringCol, ForeignKey, MultipleJoin

from canonical.launchpad.interfaces import ArchiveNotRegistered
from canonical.launchpad.interfaces import RevisionNotRegistered
from canonical.launchpad.interfaces import RevisionAlreadyRegistered
from canonical.launchpad.interfaces import VersionNotRegistered
from canonical.launchpad.interfaces import VersionAlreadyRegistered
from canonical.launchpad.interfaces import BranchAlreadyRegistered
from canonical.launchpad.interfaces import CategoryAlreadyRegistered

from zope.interface import implements
from canonical.launchpad.interfaces import IBranch

from canonical.launchpad.database.archarchive import ArchiveMapper,\
                                                     ArchNamespace,\
                                                     ArchArchive

import pybaz as arch

class Branch(SQLBase):
    """An ordered revision sequence in arch"""

    implements(IBranch)

    _table = 'Branch'
    archnamespace = ForeignKey(foreignKey='ArchNamespace', dbName='archnamespace',
                           notNull=True)
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
    

class CategoryMapper(object):
    """Map categories to and from the database"""
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
        """insert a category into the database"""
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
        except ArchiveNotRegistered, e:
            return False
        where = ("archarchive = %s AND category = %s"
                 % (quote(id), quote(category.nonarch)))
        return bool(ArchNamespace.select(where).count())

class BranchMapper(object):
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
        #    % (quote(archive_id), quote(branch.category.name))
        #)
        query = (
            "archarchive = %s AND category = %s AND branch IS NULL"
            % (quote(archive_id), quote(branch.category.name))
        )
        for an in ArchNamespace.select(query):
            print 'deleting %r (%d) from BM.insert' % (an, an.id)
            an.destroySelf()

    def exists(self, branch):
        id = ArchiveMapper()._getId(branch.category.archive)
        where = ("archarchive = %s AND category = %s AND branch = %s"
                 % (quote(id), quote(branch.category.name), quote(branch.name)))
        return bool(ArchNamespace.select(where).count())

class VersionMapper(object):
    """Map versions to and from the database"""
    def findByName(self, name):
        try:
            print name
            parser=arch.NameParser(name)
            archive=ArchArchive.select('name = ' + quote(parser.get_archive()))[0]
            id = archive.id
            query = ("archarchive = %s AND category = %s AND branch = %s "
                 "AND version = %s" 
                 % (quote(id), quote(parser.get_category()),
                    quote(parser.get_branch()), quote(parser.get_version())))
            versions = ArchNamespace.select(query)
        except IndexError, e:
            return broker.MissingVersion(name)
        count = versions.count()
        from canonical.arch import broker
        if count == 0:
            return broker.MissingVersion(name)
        if count == 1:
            # migration code to allow access to the real Version 
            # and yes, this should be tidied - by moving all to native sqlobject.
            where = ("archnamespace = %d" % versions[0].id) 
            resultset=Branch.select(where)
            if resultset.count() == 0:
                raise VersionNotRegistered(version.fullname)
            return resultset[0]
        else:
            raise RuntimeError, "Name %r found %d results" % (name, count)

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
        result = Branch(archnamespace=namespace.id,
            title='',
            description='',
        )

        #ArchNamespace._connection.query(
        #    "DELETE FROM ArchNamespace "
        #    "WHERE archarchive = %s AND category = %s AND branch = %s "
        #    "AND version IS NULL"
        #    % (quote(archive_id), quote(version.branch.category.name),
        #       quote(version.branch.name))
        #)
        query = (
            "archarchive = %s AND category = %s AND branch = %s "
            "AND version IS NULL"
            % (quote(archive_id), quote(version.branch.category.name),
               quote(version.branch.name))
        )
        for an in ArchNamespace.select(query):
            print 'deleting %r (%d) from VM.insert' % (an, an.id)
            an.destroySelf()
        return result

    def findVersionQuery(self, version):
        id = ArchiveMapper()._getId(version.branch.category.archive)
        return ("archarchive = %s AND category = %s AND branch = %s "
                 "AND version = %s" 
                 % (quote(id), quote(version.branch.category.nonarch),
                    quote(version.branch.name), quote(version.name)))

    def exists(self, version):
        return bool(ArchNamespace.select(self.findVersionQuery(version)).count())

    def _getId(self, version):
        try:
            return ArchNamespace.select(self.findVersionQuery(version))[0].id
        except IndexError, e:
            raise VersionNotRegistered(version.fullname)
 
    def _getDBBranch(self, version):
        id=self._getId(version)
        where = ("archnamespace = %d" % id) 
        resultset=Branch.select(where)
        if resultset.count() == 0:
            raise VersionNotRegistered(version.fullname)
        return resultset[0]

    def _getDBBranchId(self, version):
        return self._getDBBranch(version).id


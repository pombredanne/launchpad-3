

import psycopg

from canonical.database.sqlbase import quote, SQLBase
from sqlobject import StringCol, BoolCol, ForeignKey, IntCol, DateTimeCol, \
                      MultipleJoin

from canonical.launchpad.interfaces import ArchiveAlreadyRegistered, ArchiveNotRegistered, ArchiveLocationDoublyRegistered
from canonical.launchpad.interfaces import RevisionNotRegistered
from canonical.launchpad.interfaces import RevisionAlreadyRegistered
from canonical.launchpad.interfaces import VersionNotRegistered
from canonical.launchpad.interfaces import VersionAlreadyRegistered
from canonical.launchpad.interfaces import BranchAlreadyRegistered
from canonical.launchpad.interfaces import CategoryAlreadyRegistered

from zope.interface import implements
from canonical.launchpad.interfaces import IBranch

# XXX: This import is somewhat circular, but launchpad/database/__init__.py
# imports archarchive before archbranch, so it should be ok...
#  - Andrew Bennetts, 2004-10-20
from canonical.launchpad.database import ArchiveMapper, ArchNamespace

class Branch(SQLBase):
    """An ordered revision sequence in arch"""

    implements(IBranch)

    _table = 'branch'
    _columns = [
        ForeignKey(name='namespace', foreignKey='ArchNamespace', dbName='archnamespace',
                  notNull=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        ForeignKey(name='owner', foreignKey='Person', dbName='owner',
                   default=None),
    ]
    changesets = MultipleJoin('Changeset', joinColumn='branch')
    subjectRelations = MultipleJoin('BranchRelationship', joinColumn='subject')
    objectRelations = MultipleJoin('BranchRelationship', joinColumn='object')

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
        count = Version.select('name = ' + quote(name)).count()
        from canonical.arch import broker
        if count == 0:
            return broker.MissingVersion(name)
        if count == 1:
            return broker.Version(name)
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
        Branch(namespace=namespace.id,
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

    def exists(self, version):
        id = ArchiveMapper()._getId(version.branch.category.archive)
        where = ("archarchive = %s AND category = %s AND branch = %s "
                 "AND version = %s" 
                 % (quote(id), quote(version.branch.category.nonarch),
                    quote(version.branch.name), quote(version.name)))
        return bool(ArchNamespace.select(where).count())

    def _getId(self, version, cursor=None):
        where = ("category = %s AND branch = %s AND version = %s" 
                 % (quote(version.branch.category.nonarch),
                    quote(version.branch.name), quote(version.name)))
        try:
            return ArchNamespace.select(where)[0].id
        except IndexError, e:
            raise VersionNotRegistered(version.fullname)
            
    def _getDBBranchId(self, version):
        id=self._getId(version)
        where = ("archnamespace = %d" % id) 
        try:
            return Branch.select(where)[0].id
        except IndexError, e:
            raise VersionNotRegistered(version.fullname)


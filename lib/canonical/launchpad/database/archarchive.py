# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['archive_present', 'createBranch', 'Archive', 'ArchArchive',
           'ArchiveLocation', 'ArchNamespace', 'ArchiveLocationMapper',
           'ArchiveMapper']

import warnings
from canonical.database.sqlbase import quote, SQLBase
from sqlobject import (
    StringCol, BoolCol, ForeignKey, SQLObjectMoreThanOneResultError)

from canonical.launchpad.interfaces import (
    ArchiveNotRegistered, ArchiveLocationDoublyRegistered, NameNotAvailable)

from canonical.lp.dbschema import EnumCol
from canonical.lp.dbschema import ArchArchiveType


def archive_present(archive_name):
    results = Archive.select('name = ' + quote(archive_name))
    return bool(results.count())

def createBranch(repository):
    archive, rest = repository.split('/', 1)
    category, branchname = repository.split('--', 2)[:2]
    archive = Archive.selectOneBy(name=archive)
    if archive is None:
        raise RuntimeError, "No archive '%r' in DB" % (archive, )

    archnamespace = ArchNamespace.selectOneBy(
        archive=archive,
        category=category,
        branch=branch,
        )
    if archnamespace is None:
        archnamespace = ArchNamespace(
            archive=archive,
            category=category,
            branch=branchname,
            visible=False,
            )

    branch = Branch.selectOneBy(archnamespace=archnamespace)
    if branch is None:
        branch = Branch(
            archnamespace=archnamespace,
            title=branchname,
            description='', # FIXME
            )

    return branch


class Archive(SQLBase):
    """ArchArchive table"""

    _table = 'ArchArchive'
    name = StringCol(dbName='name', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    visible = BoolCol(dbName='visible', notNull=True)
    owner = ForeignKey(foreignKey='Person', dbName='owner', default=None)


class ArchArchive(SQLBase):
    """ArchArchive table"""

    # FIXME: This is a gratuitously stupid duplicate.
    _table = 'ArchArchive'
    name = StringCol(dbName='name', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    visible = BoolCol(dbName='visible', notNull=True)
    owner = ForeignKey(foreignKey='Person', dbName='owner')


class ArchiveLocation(SQLBase):
    """ArchArchiveLocation table"""

    _table = 'ArchArchiveLocation'
    archive = ForeignKey(foreignKey='Archive', dbName='archive')
    archivetype = EnumCol(dbName='archivetype', notNull=True,
                          schema=ArchArchiveType)
    url = StringCol(dbName='url', notNull=True)
    gpgsigned = BoolCol(dbName='gpgsigned', notNull=True)


class ArchNamespace(SQLBase):
    """A namespace in Arch (archive/category--branch--version)"""

    _table = 'ArchNamespace'
    archive = ForeignKey(foreignKey='Archive', dbName='archarchive',
                         notNull=True)
    category = StringCol(dbName='category', notNull=True)
    branch = StringCol(dbName='branch', default=None)
    version = StringCol(dbName='version', default=None)
    visible = BoolCol(dbName='visible', notNull=True)


class ArchiveLocationMapper:
    """I map ArchiveLocations to and from the database"""

    def get(self, archive, type=None):
        archiveMapper = ArchiveMapper()
        where = 'archive = ' + quote(archiveMapper._getId(archive))
        if type is not None:
            where += ' AND archivetype = %d' % type.value
        results = ArchiveLocation.select(where)
        from canonical.arch import broker
        return [broker.ArchiveLocation(archive, r.url, r.archivetype)
                for r in results]

    def getAll(self, archive):
        return self.get(archive)

    def getSome(self, archive, type):
        return self.get(archive, type=type)

    def locationExists(self, location):
        """Does the location already exist in the database?"""
        where = 'url = ' + quote(location.url)
        try:
            location = ArchiveLocation.selectOne(where)
        except SQLObjectMoreThanOneResultError:
            raise ArchiveLocationDoublyRegistered(location)
        return location is not None

    def updateLocation(self, location):
        """Update an existing location's metadata."""
        raise NotImplementedError

    def insertLocation(self, location):
        """Insert a new location into the database."""
        ArchiveLocation(
            archive=ArchiveMapper()._getId(location.archive),
            archivetype=location._type,
            url=location.url,
            gpgsigned=True,
            )

    def writeLocation(self, location):
        """Write a location entry to the db.  if it exists, update it, if not
        insert it.
        """
        raise NotImplementedError
        # if self.locationExists(location)
        #     self.updateLocation(location)
        # else:
        #     self.createLocation(location)

    def isItSigned(self, location):
        """Is this archive location signed?"""
        raise NotImplementedError


class ArchiveMapper:
    """I map Archives to and from the database."""

    def findByMatchingName(self, pattern):
        where = 'name LIKE ' + quote(pattern)
        from canonical.arch import broker
        return [broker.Archive(archive.name)
                for archive in Archive.select(where, orderBy='name')]

    def findByName(self, name):
        result = Archive.selectOne('name = ' + quote(name))
        from canonical.arch import broker
        if result is None:
            return broker.MissingArchive(name)
        else:
            return broker.Archive(name)

    def _getId(self, archive, cursor=None):
        if cursor is not None:
            warnings.warn('ArchiveMapper._getId cursor argument is deprecated',
                          DeprecationWarning, stacklevel=2)
        where = 'name = ' + quote(archive.name)
        result = Archive.selectOne(where)
        if result is None:
            raise ArchiveNotRegistered(archive.name)
        else:
            return result.id

    def insert(self, archive, title='', description=''):
        """Insert archive into the database."""
        if self.findByName(archive.name).exists():
            raise NameNotAvailable(
                "archive %s already exists" % archive.name)
        Archive(name=archive.name, title=title, description=description,
                visible=True)




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


def archive_present(archive_name):
    results = Archive.select('name = ' + quote(archive_name))
    return bool(results.count())


def createBranch(repository):
    archive, rest = repository.split('/', 1)
    category, branchname = repository.split('--', 2)[:2]

    try:
        archive = Archive.selectBy(name=archive)[0]
    except IndexError:
        raise RuntimeError, "No archive '%r' in DB" % (archive,)

    try:
        archnamespace = ArchNamespace.selectBy(
            archive=archive,
            category=category,
            branch=branch,
        )[0]
    except IndexError:
        archnamespace = ArchNamespace(
            archive=archive,
            category=category,
            branch=branchname,
            visible=False,
        )
    
    try:
        branch = Branch.selectBy(archnamespace=archnamespace)[0]
    except IndexError:
        branch = Branch(
            archnamespace=archnamespace,
            title=branchname,
            description='', # FIXME
        )
    
    return branch


class Archive(SQLBase):
    """ArchArchive table"""
        
    _table = 'ArchArchive'
    _columns = [
        StringCol('name', dbName='name', notNull=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        BoolCol('visible', dbName='visible', notNull=True),
        ForeignKey(name='owner', foreignKey='Person', dbName='owner',
                   default=None),
    ]
    
class ArchArchive(SQLBase):
    """ArchArchive table"""

    # FIXME: This is a gratuitously stupid duplicate.
    _table = 'ArchArchive'
    _columns = [
        StringCol('name', dbName='name', notNull=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        BoolCol('visible', dbName='visible', notNull=True),
        ForeignKey(name='owner', foreignKey='Person', dbName='owner'),
    ]

class ArchiveLocation(SQLBase):
    """ArchArchiveLocation table"""
    
    _table = 'ArchArchiveLocation'
    _columns = [
        ForeignKey(name='archive', foreignKey='Archive', dbName='archive'),
        IntCol('archivetype', dbName='archivetype', notNull=True),
        StringCol('url', dbName='url', notNull=True),
        BoolCol('gpgsigned', dbName='gpgsigned', notNull=True),
    ]

class ArchNamespace(SQLBase):
    """A namespace in Arch (archive/category--branch--version)"""
    _table = 'ArchNamespace'
    _columns = [
        ForeignKey(name='archive', foreignKey='Archive', dbName='archarchive',
                  notNull=True),
        StringCol('category', dbName='category', notNull=True),
        StringCol('branch', dbName='branch', default=None),
        StringCol('version', dbName='version', default=None),
        BoolCol('visible', dbName='visible', notNull=True),
    ]

class ArchiveLocationMapper(object):
    """I map ArchiveLocations to and from the database"""
    def get(self, archive, type=None):
        archiveMapper = ArchiveMapper()
        where = 'archive = ' + quote(archiveMapper._getId(archive))
        if type is not None:
            where += ' AND archivetype = ' + quote(type)
        results = ArchiveLocation.select(where)
        from canonical.arch import broker
        return [broker.ArchiveLocation(r.url, archive, r.url) for r in results]
        
    def getAll(self, archive):
        return self.get(archive)

    def getSome(self, archive, type):
        return self.get(archive, type=type)

    def locationExists(self, location):
        """Does the location already exist in the database?"""
        where = 'url = ' + quote(location.url)
        count = ArchiveLocation.select(where).count()
        if count == 1:
            return True
        elif count == 0:
            return False
        else:
            raise ArchiveLocationDoublyRegistered("Er, why is the same url in the database more than once?")

    def updateLocation(self, location):
        """Update an existing location's metadata"""
        raise RuntimeError("Nothing here yet")

    def insertLocation(self, location):
        """insert a new location into the database"""
#        print ArchiveMapper()._getId(location.archive), location._type, location.url, True
        ArchiveLocation(
            archive=ArchiveMapper()._getId(location.archive),
            archivetype=location._type,
            url=location.url,
            gpgsigned=True,
        )

    def writeLocation(self, location):
        """Write a location entry to the db.  if it exists, update it, if not insert it."""
        # if self.locationExists(location)
        #     self.updateLocation(location)
        # else:
        #     self.createLocation(location)

    def isItSigned(self, location):
        """Is this archive location signed?"""
        pass

class ArchiveMapper(object):
    """I map Archives to and from the database"""

    def findByMatchingName(self, pattern):
        where = 'name LIKE ' + quote(pattern)
        from canonical.arch import broker
        return [broker.Archive(archive.name) for archive in 
                Archive.select(where, orderBy='name')]
        
    def findByName(self, name):
        results = Archive.select('name = ' + quote(name))
        count = len(list(results))
        from canonical.arch import broker
        if count == 0:
            return broker.MissingArchive(name)
        if count == 1:
            return broker.Archive(name)
        else:
            raise RuntimeError, "Name %r found several: %r" % (name, results)

    def _getId(self, archive, cursor=None):
        #warnings.warn('Passing a cursor to ArchiveMapper._getId is deprecated',
        #              DeprecationWarning, stacklevel=2)
        where = 'name = ' + quote(archive.name)
        results = Archive.select(where)
        try:
            return results[0].id
        except IndexError:
            raise ArchiveNotRegistered(archive.name)
        
    def insert(self, archive):
        """Insert archive into the database"""
        if self.findByName(archive.name).exists():
            raise KeyError("archive %s already exists" % archive.name)
        Archive(name=archive.name, title='', description='', 
                            visible=True)


from canonical.database.sqlbase import quote, SQLBase
from sqlobject import StringCol, BoolCol, ForeignKey

from canonical.launchpad.interfaces import ArchiveNotRegistered, ArchiveLocationDoublyRegistered
from canonical.launchpad.interfaces import RevisionNotRegistered
from canonical.launchpad.interfaces import RevisionAlreadyRegistered
from canonical.launchpad.interfaces import VersionNotRegistered
from canonical.launchpad.interfaces import VersionAlreadyRegistered
from canonical.launchpad.interfaces import BranchAlreadyRegistered
from canonical.launchpad.interfaces import CategoryAlreadyRegistered
from canonical.launchpad.interfaces import IBranch

from canonical.lp.dbschema import EnumCol
from canonical.lp.dbschema import ArchArchiveType

#
#
#

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


class ArchiveLocationMapper(object):
    """I map ArchiveLocations to and from the database"""
    def get(self, archive, type=None):
        archiveMapper = ArchiveMapper()
        where = 'archive = ' + quote(archiveMapper._getId(archive))
        if type is not None:
            where += ' AND archivetype = %d' % type.value
        results = ArchiveLocation.select(where)
        from canonical.arch import broker
        return [broker.ArchiveLocation(archive, r.url, r.archivetype) for r in results]
        
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
        import warnings
        if cursor is not None:
            warnings.warn('ArchiveMapper._getId cursor argument is deprecated',
                          DeprecationWarning, stacklevel=2)
        where = 'name = ' + quote(archive.name)
        results = Archive.select(where)
        try:
            return results[0].id
        except IndexError:
            raise ArchiveNotRegistered(archive.name)
        
    def insert(self, archive, title='', description=''):
        """Insert archive into the database"""
        if self.findByName(archive.name).exists():
            raise KeyError("archive %s already exists" % archive.name)
        Archive(name=archive.name, title=title, description=description, 
                visible=True)


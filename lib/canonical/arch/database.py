# arch-tag: 0b969817-f8a9-4a99-bb02-b4b2e749845b
#
# Copyright (C) 2004 Canonical Software
# 	Authors: Rob Weir <rob.weir@canonical.com>
#		 Robert Collins <robert.collins@canonical.com>

# higher-level callers are responsible for splitting these into transactions.

import canonical.arch, sys
canonical.arch.database = sys.modules['canonical.arch.database']
from canonical.arch import broker
from canonical.database.sqlbase import quote, SQLBase
from canonical.arch.interfaces import ArchiveAlreadyRegistered, ArchiveNotRegistered, ArchiveLocationDoublyRegistered

from sqlobject import StringCol, BoolCol, ForeignKey, IntCol, DateTimeCol, \
                      MultipleJoin
import warnings

def dbname():
    return 'dbname=launchpad_test'

DBHandle = None

def connect():
    global DBHandle
    from sqlobject import connectionForURI
    from canonical.database.sqlbase import SQLBase
    conn = connectionForURI('postgres:///launchpad_test')
    SQLBase.initZopeless(conn)
    DBHandle = conn.getConnection()

#connect()

def nuke():
    if not DBHandle:
        connect()
    cursor = DBHandle.cursor()
    cursor.execute("DELETE FROM ChangesetFileHash")    
    cursor.execute("DELETE FROM ChangesetFile")
    cursor.execute("DELETE FROM ChangesetFileName")
    cursor.execute("DELETE FROM Changeset")
    cursor.execute("DELETE FROM Branch")
    cursor.execute("DELETE FROM ArchNamespace")
    cursor.execute("DELETE FROM ArchArchiveLocation")
    cursor.execute("DELETE FROM ArchArchive")
    commit()

def commit():
    DBHandle.commit()

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

class Branch(SQLBase):
    """An ordered revision sequence in arch"""

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
        from canonical.soyuz.database import BranchRelationship
        BranchRelationship(subject=self, object=branch, label=relationship)

    def getRelations(self):
        return tuple(self.subjectRelations) + tuple(self.objectRelations)
    

class Changeset(SQLBase):
    """A changeset"""

    _table = 'changeset'
    _columns = [
        ForeignKey(name='branch', foreignKey='Branch', dbName='branch',
                   notNull=True),
        DateTimeCol('datecreated', dbName='datecreated', notNull=True),
        StringCol('name', dbName='name', notNull=True),
        StringCol('logmessage', dbName='logmessage', notNull=True),
        ForeignKey(name='archID', foreignKey='ArchUserID', dbName='archID',
                   default=None),
        ForeignKey(name='gpgkey', foreignKey='GPGKey', dbName='gpgkey',
                   default=None),
    ]

class ChangesetFileName(SQLBase):
    """A filename from a changeset"""

    _table = 'ChangeSetFileName'
    _columns = [StringCol('filename', dbName='filename', notNull=True, unique=True)]
    
class ChangesetFile(SQLBase):
    _table = 'ChangesetFile'
    _columns = [
        ForeignKey(name='changeset', foreignKey='Changeset', 
                   dbName='changeset', notNull=True),
        ForeignKey(name='changesetfilename', foreignKey='ChangesetFileName', 
                   dbName='changesetfilename', notNull=True),
        StringCol('filecontents', dbName='filecontents', notNull=True),
        IntCol('filesize', dbName='filesize', notNull=True),
    ]

class ChangesetFileHash(SQLBase):
    _table = 'ChangesetFileHash'
    _columns = [
        ForeignKey(name='changesetfile', foreignKey='ChangesetFile', 
                   dbName='changesetfile', notNull=True),
        IntCol('hashalg', dbName='hashalg', notNull=True),
        StringCol('hash', dbName='hash', notNull=True),
    ]

def archive_present(archive_name):
    results = Archive.select('name = ' + quote(archive_name))
    return bool(results.count())

def _archive_purge(archive_name):
    """I purge an archive from the database. I AM ONLY for use during testing.
    once in production the database fields are update-once."""
    c = DBHandle.cursor()
    m = ArchiveMapper()
    try:
        archive_id = m._getId(broker.Archive(archive_name), c)
    except ArchiveNotRegistered, e:
        return
    c.execute("SELECT archnamespace.id from archnamespace inner join archarchive on archnamespace.archarchive=archarchive.id where archarchive.name like '%s'" % archive_id)
    namespaces=c.fetchall()
    for namespace in namespaces:
        c.execute("DELETE FROM Branch WHERE archnamespace = %d" % namespace[0])
    c.execute("DELETE FROM ArchArchiveLocation WHERE archive like '%s'" % archive_id)
    c.execute("DELETE FROM ArchArchive WHERE name like '%s'" % archive_name)

class ArchiveLocationMapper(object):
    """I map ArchiveLocations to and from the database"""
    def get(self, archive, type=None):
        archiveMapper = ArchiveMapper()
        where = 'archive = ' + quote(archiveMapper._getId(archive))
        if type is not None:
            where += ' AND archivetype = ' + quote(type)
        results = ArchiveLocation.select(where)
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
        return [broker.Archive(archive.name) for archive in 
                Archive.select(where, orderBy='name')]
        
    def findByName(self, name):
        results = Archive.select('name = ' + quote(name))
        count = len(list(results))
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

class CategoryMapper(object):
    """Map categories to and from the database"""
    def findByName(self, name):
        count = Category.select('category = ' + quote(name)).count()
        if count == 0:
            return broker.MissingCategory(name)
        if count == 1:
            return broker.Category(name)
        else:
            raise RuntimeError, "Name %r found %d results" % (name, count)

    def insert(self, category):
        """insert a category into the database"""
        from canonical.arch.interfaces import CategoryAlreadyRegistered
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
        if count == 0:
            return broker.MissingBranch(name)
        if count == 1:
            return broker.Branch(name)
        else:
            raise RuntimeError, "Name %r found %d results" % (name, count)

    def insert(self, branch):
        """insert a branch into the database"""
        from canonical.arch.interfaces import BranchAlreadyRegistered
        if self.exists(branch):
            raise BranchAlreadyRegistered(branch.fullname)
        archive_id = ArchiveMapper()._getId(branch.category.archive)
        ArchNamespace(
            archive=archive_id,
            category=branch.category.name,
            branch=branch.name,
            visible=True,
        )

        ArchNamespace._connection.query(
            "DELETE FROM ArchNamespace "
            "WHERE archarchive = %s AND category = %s AND branch IS NULL"
            % (quote(archive_id), quote(branch.category.name))
        )

    def exists(self, branch):
        id = ArchiveMapper()._getId(branch.category.archive)
        where = ("archarchive = %s AND category = %s AND branch = %s"
                 % (quote(id), quote(branch.category.name), quote(branch.name)))
        return bool(ArchNamespace.select(where).count())

class VersionMapper(object):
    """Map versions to and from the database"""
    def findByName(self, name):
        count = Version.select('name = ' + quote(name)).count()
        if count == 0:
            return broker.MissingVersion(name)
        if count == 1:
            return broker.Version(name)
        else:
            raise RuntimeError, "Name %r found %d results" % (name, count)

    def insert(self, version):
        """insert a version into the database"""
        from canonical.arch.interfaces import VersionAlreadyRegistered
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

        ArchNamespace._connection.query(
            "DELETE FROM ArchNamespace "
            "WHERE archarchive = %s AND category = %s AND branch = %s "
            "AND version IS NULL"
            % (quote(archive_id), quote(version.branch.category.name),
               quote(version.branch.name))
        )

    def exists(self, version):
        id = ArchiveMapper()._getId(version.branch.category.archive)
        where = ("archarchive = %s AND category = %s AND branch = %s "
                 "AND version = %s" 
                 % (quote(id), quote(version.branch.category.nonarch),
                    quote(version.branch.name), quote(version.name)))
        return bool(ArchNamespace.select(where).count())

    def _getId(self, version, cursor=None):
        from canonical.arch.interfaces import VersionNotRegistered
        where = ("category = %s AND branch = %s AND version = %s" 
                 % (quote(version.branch.category.nonarch),
                    quote(version.branch.name), quote(version.name)))
        try:
            return ArchNamespace.select(where)[0].id
        except IndexError, e:
            raise VersionNotRegistered(version.fullname)
            
    def _getDBBranchId(self, version):
        from canonical.arch.interfaces import VersionNotRegistered
        id=self._getId(version)
        where = ("archnamespace = %d" % id) 
        try:
            return Branch.select(where)[0].id
        except IndexError, e:
            raise VersionNotRegistered(version.fullname)

class RevisionMapper(object):
    """Map revisions in and out of the db"""
    def findByName(self, name):
        from arch import NameParser
        if self.exists(name):
            parser = NameParser(name)
            archive = broker.Archive(parser.get_archive())
            category = broker.Category(parser.get_category(), archive)
            branch = broker.Branch(parser.get_branch(), category)
            version = broker.Version(parser.get_version(), branch)
            return broker.Revision(parser.get_revision(), version)

    def insert(self, revision):
        """insert a revision into the database"""
        from canonical.arch.interfaces import RevisionAlreadyRegistered
        if self.exists(revision):
            raise RevisionAlreadyRegistered(revision.fullname)
        #FIXME: ask Mark if we should include correct date?
        revision.set_changeset(Changeset(
            branch=VersionMapper()._getDBBranchId(revision.version),
            datecreated='now',
            name=revision.name,
            logmessage='',
        ))

    def changeset(self, revision):
        """get a cset object"""
        mapper = VersionMapper()
        version_id = mapper._getDBBranchId(revision.version)
        where = 'name = ' + quote(revision.name) + ' and branch = ' + str(version_id)
        return Changeset.select(where)[0]

    def update_log(self, revision, log):
        """Update a revision's log in the database"""
        cursor = DBHandle.cursor()
        log = quote(log)
        revision.log_message = log

    def exists(self, revision):
        """does revision exist in the archice?"""
        mapper = VersionMapper()
        version_id = mapper._getDBBranchId(revision.version)
        where = 'name = ' + quote(revision.name) + ' and branch = ' + str(version_id)
        return bool(Changeset.select(where).count())
 
    def _getId(self, revision, cursor):
        """Get the id of a revision"""
        from canonical.arch.interfaces import RevisionNotRegistered
        branch_id = VersionMapper()._getId(revision.version, cursor)
        cursor.execute("SELECT id FROM Changeset WHERE name = '%s' AND branch = %d" % (revision.name, branch_id))
        try:
            return cursor.fetchone()[0]
        except IndexError, e:
            raise RevisionNotRegistered(revision.fullname)
        
    def insert_file(self, revision, filename, data, checksums):
        """Insert a file into the database"""
        size = len(data)
        import psycopg
        name = ChangesetFileName.select('filename = %s' % quote(filename))
        if name.count() == 0:
            #        data = psycopg.Binary(data)
            name = ChangesetFileName(filename=filename)
        else:
            name = name[0]

#        print "CSET = %s (named %s)" % (revision.changeset, revision.fullname)
#        revision.get_changeset()
#        print "CSET = %s" % revision.changeset

        f = ChangesetFile(changeset=revision.changeset.id,
                          changesetfilename=name.id,
                          filecontents="",
                          filesize=size)
        for hashalg, hashval in checksums.items():
            hashid = {"md5":0, "sha1":1}[hashalg]
            hasha = ChangesetFileHash(changesetfile=f.id,
                                      hashalg=hashid,
                                      hash=hashval)

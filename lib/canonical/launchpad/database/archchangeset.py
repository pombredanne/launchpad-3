from canonical.database.sqlbase import quote, SQLBase
from sqlobject import StringCol, ForeignKey, IntCol
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.interfaces import RevisionNotRegistered
from canonical.launchpad.interfaces import RevisionAlreadyRegistered
from canonical.launchpad.interfaces import VersionNotRegistered
from canonical.launchpad.interfaces import VersionAlreadyRegistered
from canonical.launchpad.interfaces import BranchAlreadyRegistered
from canonical.launchpad.interfaces import CategoryAlreadyRegistered

from canonical.launchpad.interfaces import IBranch

from canonical.launchpad.database.archbranch import VersionMapper
from canonical.lp.dbschema import EnumCol
from canonical.lp.dbschema import HashAlgorithms

class Changeset(SQLBase):
    """A changeset"""

    _table = 'changeset'
    _columns = [
        ForeignKey(name='branch', foreignKey='Branch', dbName='branch',
                   notNull=True),
        UtcDateTimeCol('datecreated', dbName='datecreated', notNull=True),
        StringCol('name', dbName='name', notNull=True),
        StringCol('logmessage', dbName='logmessage', notNull=True),
        ForeignKey(name='archID', foreignKey='ArchUserID', dbName='archID',
                   default=None),
        ForeignKey(name='gpgkey', foreignKey='GPGKey', dbName='gpgkey',
                   default=None),
    ]

    def getPackageName(self):
        """Arch package name for the changeset."""
        packagename = self.branch.getPackageName()
        packagename += "--" + self.name
        return packagename

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
        EnumCol('hashalg', dbName='hashalg', notNull=True,
                schema=HashAlgorithms),
        StringCol('hash', dbName='hash', notNull=True),
    ]

class RevisionMapper(object):
    """Map revisions in and out of the db"""
    def findByName(self, name):
        from arch import NameParser
        from canonical.arch import broker
        if self.exists(name):
            parser = NameParser(name)
            archive = broker.Archive(parser.get_archive())
            category = broker.Category(parser.get_category(), archive)
            branch = broker.Branch(parser.get_branch(), category)
            version = broker.Version(parser.get_version(), branch)
            return broker.Revision(parser.get_revision(), version)

    def insert(self, revision):
        """insert a revision into the database"""
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
        branch_id = VersionMapper()._getId(revision.version, cursor)
        cursor.execute("SELECT id FROM Changeset WHERE name = '%s' AND branch = %d" % (revision.name, branch_id))
        try:
            return cursor.fetchone()[0]
        except IndexError, e:
            raise RevisionNotRegistered(revision.fullname)
        
    def insert_file(self, revision, filename, data, checksums):
        from canonical.lp.dbschema import HashAlgorithms
        """Insert a file into the database"""
        size = len(data)
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
            hash_mapping = {"md5": HashAlgorithms.MD5,
                            "sha1": HashAlgorithms.SHA1}
            hashid = hash_mapping[hashalg]
            hasha = ChangesetFileHash(changesetfile=f.id,
                                      hashalg=hashid,
                                      hash=hashval)


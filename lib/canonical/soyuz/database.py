# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol, \
                      DateTimeCol
from sqlobject.sqlbuilder import func
from canonical.arch.sqlbase import SQLBase
from canonical.lp import dbschema

# Soyuz interfaces
from canonical.soyuz.interfaces import ISourcePackageRelease, IManifestEntry
from canonical.soyuz.interfaces import IBranch, IChangeset
from canonical.soyuz.interfaces import ISourcePackage, IPerson


class Distribution(SQLBase):
    """An open source distribution."""

    _table = 'Distribution'
    _columns = [
        StringCol('name', dbName='name', notNull=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        ForeignKey(name='owner', foreignKey='Person', dbName='owner', 
                   notNull=True),
    ]


class SourcePackage(SQLBase):
    """A source package, e.g. apache2."""

    implements(ISourcePackage)

    _table = 'SourcePackage'
    _columns = [
        ForeignKey(name='maintainer', foreignKey='Person', dbName='maintainer',
                   notNull=True),
        StringCol('name', dbName='name', notNull=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        ForeignKey(name='manifest', foreignKey='Manifest', dbName='manifest', 
                   default=None),
    ]
    releases = MultipleJoin('SourcePackageRelease',
                            joinColumn='sourcepackage')

    def getManifest(self):
        return self.manifest

    def getRelease(self, version):
        return SourcePackageRelease.selectBy(version=version)[0]


class SourcePackageRelease(SQLBase):
    """A source package release, e.g. apache 2.0.48-3"""
    
    implements(ISourcePackageRelease)

    _table = 'SourcePackageRelease'
    _columns = [
        StringCol('version', dbName='Version'),
        ForeignKey(name='creator', foreignKey='Person', dbName='creator'),
        ForeignKey(name='sourcepackage', foreignKey='SourcePackage',
                   dbName='sourcepackage', notNull=True),
    ]


def getSourcePackage(name):
    return SourcePackage.selectBy(name=name)


def createSourcePackage(name, maintainer=0):
    # FIXME: maintainer=0 is a hack.  It should be required (or the DB shouldn't
    #        have NOT NULL on that column).
    return SourcePackage(
        name=name, 
        maintainer=maintainer,
        title='', # FIXME
        description='', # FIXME
    )

def createBranch(repository):
    from canonical.arch.database import Archive, Branch, ArchNamespace

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
        

    
class Manifest(SQLBase):
    """A manifest"""

    _table = 'Manifest'
    _columns = [
        DateTimeCol('datecreated', dbName='datecreated', notNull=True,
                default=func.NOW),
    ]
    entries = MultipleJoin('ManifestEntry', joinColumn='manifest')

    def __iter__(self):
        return self.entries


class ManifestEntry(SQLBase):
    """A single entry in a manifest"""

    implements(IManifestEntry)
    
    _table = 'manifestentry'
    _columns = [
        ForeignKey(name='manifest', foreignKey='Manifest', dbName='manifest', 
                   notNull=True),
        IntCol(name='sequence', dbName='sequence', notNull=True),
        ForeignKey(name='branch', foreignKey='Branch', dbName='branch', 
                   notNull=True),
        ForeignKey(name='changeset', foreignKey='Changeset', 
                   dbName='changeset'),
        IntCol(name='entrytype', dbName='entrytype', notNull=True),
        StringCol(name='path', dbName='path', notNull=True),
        IntCol(name='patchon', dbName='patchon'),
        StringCol(name='dirname', dbName='dirname'),
    ]


class BranchRelationship(SQLBase):
    """A relationship between branches.
    
    e.g. "subject is a debianization-branch-of object"
    """

    _table = 'BranchRelationship'
    _columns = [
        ForeignKey(name='subject', foreignKey='Branch', dbName='subject', 
                   notNull=True),
        IntCol(name='label', dbName='label', notNull=True),
        ForeignKey(name='object', foreignKey='Branch', dbName='subject', 
                   notNull=True),
    ]

    def _get_src(self):
        return self.subject
    def _set_src(self, value):
        self.subject = value

    def _get_dst(self):
        return self.object
    def _set_dst(self, value):
        self.object = value

    def _get_labelText(self):
        # FIXME: There should be a better way to look up a schema item given its
        #        value
        return [br for br in dbschema.BranchRelationships
                if br == self.label][0]
        

class SoyuzProduct(SQLBase):

    _table = 'Product'

    _columns = [
        ForeignKey(name='project', foreignKey='Project', dbName='project',
                   notNull=True),
        ForeignKey(name='owner', foreignKey='Person', dbName='owner',
                   notNull=True),
        StringCol('name', dbName='name', notNull=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        DateTimeCol('datecreated', dbName='datecreated', notNull=True,
                    default="NOW"),
        StringCol('homepageurl', dbName='homepageurl'),
        StringCol('screenshotsurl'),
        StringCol('wikiurl'),
        StringCol('programminglang'),
        StringCol('downloadurl'),
        StringCol('lastdoap'),
        ]

        

class SoyuzProject(SQLBase):

    _table = 'Project'

    _columns = [
        ForeignKey(name='owner', foreignKey='Person', dbName='owner',
                   notNull=True),
        StringCol('name', dbName='name', notNull=True),
        StringCol('title', dbName='title', notNull=True, default=""),
        StringCol('description', dbName='description', notNull=True,
                  default=""),
        DateTimeCol('datecreated', dbName='datecreated', notNull=True,
                    default="NOW"),
        StringCol('homepageurl', dbName='homepageurl'),
    ]

# arch-tag: 6c76cb93-edf7-4019-9af4-53bfeb279194

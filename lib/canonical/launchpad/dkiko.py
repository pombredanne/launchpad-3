
# Python imports
from sets import Set
from datetime import datetime

# Zope imports
from zope.interface import implements

# SQLObject/SQLBase
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
from sqlobject import StringCol, ForeignKey, IntCol, MultipleJoin, BoolCol, \
                      DateTimeCol
from sqlobject.sqlbuilder import func

from canonical.database.sqlbase import SQLBase, quote
from canonical.launchpad.database import Product, Project
from canonical.lp import dbschema

# interfaces and database 
from canonical.launchpad.interfaces import ISourcePackageRelease, IManifestEntry, \
                                           IBranch, IChangeset, \
                                           ISourcePackage, ISoyuzPerson, \
                                           IBinaryPackage, \
                                           IDistributionRole, IDistroReleaseRole, \
                                           IDistribution, IRelease, \
                                           ISourcepackage, IBinarypackage, \
                                           ISourcepackageName, IBinarypackageName, \
                                           IProcessor, IProcessorFamily, \
                                           IBuilder

from canonical.launchpad.database import Archive, Branch, ArchNamespace
from canonical.launchpad.database.person import Person
#
#
#

class SoyuzBuilder(SQLBase):
    implements(IBuilder)

    _table = 'Builder'
    _columns = [
        ForeignKey(name='processor', dbName='processor',
                   foreignKey='SoyuzProcessor', notNull=True),
        StringCol('fqdn', dbName='fqdn'),
        StringCol('name', dbName='name'),
        StringCol('title', dbName='title'),
        StringCol('description', dbName='description'),
        ForeignKey(name='owner', dbName='owner',
                   foreignKey='Person', notNull=True),
        ]
 
class SoyuzProcessor(SQLBase):
    implements(IProcessor)

    _table = 'Processor'
    _columns = [
        ForeignKey(name='family', dbName='family',
                   foreignKey='SoyuzProcessorFamily', notNull=True),
        StringCol('name', dbName='name', notNull=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        ForeignKey(name='owner', dbName='owner',
                   foreignKey='Person', notNull=True),
        ]

class SoyuzProcessorFamily(SQLBase):
    implements(IProcessorFamily)

    _table = 'ProcessorFamily'
    _columns = [
        StringCol('name', dbName='name', notNull=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        ForeignKey(name='owner', dbName='owner',
                   foreignKey='Person', notNull=True),
        ]

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
        # FIXME: There should be a better way to look up a schema
        #  item given its value
        return [br for br in dbschema.BranchRelationships
                if br == self.label][0]
        







    



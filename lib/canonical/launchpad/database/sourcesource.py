"""Launchpad SourceSource Database Table Objects

Part of the Launchpad system.

(c) 2004 Canonical, Ltd.
"""

# Zope
from zope.interface import implements

# SQL object
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol, BoolCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
from canonical.database.sqlbase import SQLBase, quote

# Launchpad interfaces
from canonical.launchpad.interfaces import *


class SourceSource(SQLBase): 
    """SourceSource table"""

    implements (ISourceSource)
    
    _table = 'SourceSource'
    _columns = [
        StringCol('name', dbName='name', notNull=True),
        StringCol('title', dbName='title', notNull=True),
        StringCol('description', dbName='description', notNull=True),
        # Mark Shuttleworth 03/10/04 Robert Collins why is this default=1?
        ForeignKey(name='product', foreignKey='Product', dbName='product',
                   default=1),
        StringCol('cvsroot', dbName='cvsroot', default=None),
        StringCol('cvsmodule', dbName='cvsmodule', default=None),
        ForeignKey(name='cvstarfile', foreignKey='LibraryFileAlias',
                   dbName='cvstarfile', default=None),
        StringCol('cvstarfileurl', dbName='cvstarfileurl', default=None),
        StringCol('cvsbranch', dbName='cvsbranch', default=None),
        StringCol('svnrepository', dbName='svnrepository', default=None),
        StringCol('releaseroot', dbName='releaseroot', default=None),
        StringCol('releaseverstyle', dbName='releaseverstyle', default=None),
        StringCol('releasefileglob', dbName='releasefileglob', default=None),
        ForeignKey(name='releaseparentbranch', foreignKey='Branch',
                   dbName='releaseparentbranch', default=None),
        ForeignKey(name='sourcepackage', foreignKey='SourcePackage',
                   dbName='sourcepackage', default=None),
        ForeignKey(name='branch', foreignKey='Branch',
                   dbName='branch', default=None),
        DateTimeCol('lastsynced', dbName='lastsynced', default=None),
        DateTimeCol('syncinterval', dbName='syncinterval', default=None),
        # WARNING: syncinterval column type is "interval", not "integer"
        # WARNING: make sure the data is what buildbot expects
        #IntCol('rcstype', dbName='rcstype', default=RCSTypeEnum.cvs,
        #       notNull=True),
        # FIXME: use 'RCSTypeEnum.cvs' rather than '1'
        IntCol('rcstype', dbName='rcstype', default=1,
               notNull=True),
        StringCol('hosted', dbName='hosted', default=None),
        StringCol('upstreamname', dbName='upstreamname', default=None),
        DateTimeCol('processingapproved', dbName='processingapproved',
                    notNull=False, default=None),
        DateTimeCol('syncingapproved', dbName='syncingapproved', notNull=False,
                    default=None),
        # For when Rob approves it
        StringCol('newarchive', dbName='newarchive'),
        StringCol('newbranchcategory', dbName='newbranchcategory'),
        StringCol('newbranchbranch', dbName='newbranchbranch'),
        StringCol('newbranchversion', dbName='newbranchversion'),
        # Temporary keybuk stuff
        StringCol('packagedistro', dbName='packagedistro', default=None),
        StringCol('packagefiles_collapsed', dbName='packagefiles_collapsed',
                default=None),
        ForeignKey(name='owner', foreignKey='Person', dbName='owner',
                   notNull=True),
        StringCol('currentgpgkey', dbName='currentgpgkey', default=None),
        StringCol('fileidreference', dbName='fileidreference', default=None),
    ]

    def branchfrom(self):
        return self.cvsbranch

    def enable(self):
        """enable the sync for processing"""
        self.processingapproved='NOW'
        self.frequency=datetime.timedelta(1)
    
    def enabled(self):
        """is the sync enabled"""
        return self.processingapproved is not None

    def autosyncing(self):
        """is the sync automatically scheduling"""
        return self.syncingapproved is not None

    def autosync(self):
        """enable autosyncing"""
        self.syncingapproved='NOW'

    def canChangeProduct(self):
        """is this sync allowed to have its product changed?"""
        return self.product.project.name=="do-not-use-info-imports" and self.product.name=="unassigned"

    def changeProduct(self, targetname):
        """change the product this sync belongs to to be 'product'"""
        assert (self.canChangeProduct())
        projectname,productname=targetname.split("/")
        project=ProjectMapper().getByName(projectname)
        product=ProductMapper().getByName(productname, project)
        self.product=product


class SourceSourceSet(object):
    """The set of SourceSource's."""
    implements(ISourceSourceSet)

    def __getitem__(self, sourcesourcename):
        #
        # Strangely, the sourcesourcename appears to have been quoted
        # already. Quoting it again causes this query to break, though we
        # are not sure why.
        #
        ss = SourceSource.select(SourceSource.q.name=="%s" % \
                                    sourcesourcename)
        return ss[0]



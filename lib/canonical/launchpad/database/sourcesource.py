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
#circular import
#from canonical.soyuz.importd import ProjectMapper, ProductMapper

# Launchpad interfaces
# XXX: Daniel Debonzi 2004-11-25
# Why RCSTypeEnum is inside launchpad.interfaces?
from canonical.launchpad.interfaces import ISourceSource, ISourceSourceSet, \
                                           RCSTypeEnum

# tools
import datetime

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

    def certifyForSync(self):
        """enable the sync for processing"""
        self.processingapproved='NOW'
        self.syncinterval=datetime.timedelta(1)
    
    def syncCertified(self):
        """is the sync enabled"""
        return self.processingapproved is not None

    def autoSyncEnabled(self):
        """is the sync automatically scheduling"""
        return self.syncingapproved is not None

    def enableAutoSync(self):
        """enable autosyncing"""
        self.syncingapproved='NOW'

    def canChangeProduct(self):
        """is this sync allowed to have its product changed?"""
        return self.product.project.name=="do-not-use-info-imports" and self.product.name=="unassigned"

    def changeProduct(self, targetname):
        """change the product this sync belongs to to be 'product'"""
        assert (self.canChangeProduct())
        projectname,productname=targetname.split("/")
        from canonical.soyuz.importd import ProjectMapper, ProductMapper
        project=ProjectMapper().getByName(projectname)
        product=ProductMapper().getByName(productname, project)
        self.product=product

    def needsReview(self):
        if not self.syncapproved and self.autotested:
            return True
        return False

    def _get_repository(self):
        if self.rcstype == RCSTypeEnum.cvs:
            return self.cvsroot
        elif self.rcstype == RCSTypeEnum.svn:
            return self.svnrepository
        else:
            # FIXME!
            return None

    # Translate importd.Job.Job's instance variables to database columns by
    # creating some simple properties.  [Note that SQLObject turns _get_* and
    # _sets_* methods into properties automagically]
    #FIXME: buildbot should updated this on mirror completion.
    def _get_TYPE(self):
 #       if self.lastsynced is None:
        if self.syncinterval is None or int(self.syncinterval) == 0:
            return 'import'
        else:
            return 'sync'
    def _get_package_files(self):
        if self.package_files_collapsed is None: return None
        return self.package_files_collapsed.split()
    def _get_RCS(self): return RCSNames[self.rcstype]
    def _set_RCS(self, value): self.rcstype = getattr(RCSTypeEnum, value)
    def _get_module(self): return self.cvsmodule
    def _set_module(self, value): self.cvsmodule = value
    def _get_category(self): return self.newbranchcategory
    def _set_category(self, value): return self.newbranchcategory
    def _get_archivename(self): return self.newarchive
    def _set_archivename(self, value): self.archivename = value
    def _get_branchfrom(self): return self.cvsbranch # FIXME: assumes cvs!
    def _set_branchfrom(self, value): self.cvsbranch = value # FIXME: ditto
    def _get_branchto(self): return self.newbranchbranch
    def _set_branchto(self, value): self.newbranchbranch = value
    def _get_archversion(self): return self.newbranchversion
    def _set_archversion(self, value): self.newbranchversion = value
    
    def buildJob(self):
        # FIXME: The rest of this method can probably be deleted now.
        # it so can't, inheritance doesn't work here.
        from importd.Job import CopyJob
        job = CopyJob()
        job.repository = str(self.repository)
 #       if self.lastsynced is None:
        if self.syncingapproved is None:
	#self.frequency is None or int(self.frequency) == 0:
            job.TYPE = 'import'
            if self.cvstarfileurl is not None and self.cvstarfileurl != "":
                job.repository = str(self.cvstarfileurl)
            job.frequency=0
        else:
            job.TYPE = 'sync'

            job.frequency=int(self.syncinterval)

        job.tagging_rules=[]

        # XXX ddaa 2004-10-28: workaround for broken cscvs shell quoting
        name = _job_name_munger.translate(self.name)
        # XXX end
        job.name = name
        job.RCS = RCSNames[self.rcstype]
        job.svnrepository = self.svnrepository
        job.module = str(self.cvsmodule)

        job.category = str(self.newbranchcategory)
        job.archivename = str(self.newarchive)
        job.branchfrom = str(self.cvsbranch) # FIXME: assumes cvs!
        job.branchto = str(self.newbranchbranch)
        job.archversion = str(self.newbranchversion)

        job.package_distro = self.packagedistro
        job.package_files = self.packagefiles_collapsed
        job.product_id = self.product.id
        return job


class _JobNameMunger(object):
    # XXX ddaa 2004-10-28: This is part of a short term workaround for
    # code in cscvs which does not perform shell quoting correctly.
    # https://bugzilla.canonical.com/bugzilla/show_bug.cgi?id=2149

    def __init__(self):
        self._table = None

    def is_munged(self, char):
        import string
        return not (char in string.ascii_letters or char in string.digits
                    or char in ",-.:=@^_" or ord(char) > 127)

    def translation_table(self):
        if self._table is not None: return self._table
        table = []
        for code in range(256):
            if self.is_munged(chr(code)):
                table.append('_')
            else:
                table.append(chr(code))
        self._table = ''.join(table)
        return self._table

    def translate(self, text):
        return text.encode('utf8').translate(self.translation_table())


# XXX ddaa 2004-10-28: workaround for broken cscvs shell quoting
_job_name_munger = _JobNameMunger()


class SourceSourceSet(object):
    """The set of SourceSource's."""
    implements(ISourceSourceSet)

    def __init__(self):
        self.syncingapproved = None
        self.processingapproved = None
        self.autotested = None
        self.projecttext = None
        self._resultset = None

    def __getitem__(self, sourcesourcename):
        # XXX Strangely, the sourcesourcename appears to have been quoted
        # already. Quoting it again causes this query to break, though we
        # are not sure why.
        ss = SourceSource.select(SourceSource.q.name=="%s" % \
                                    sourcesourcename)
        return ss[0]

    def exec_query(self):
        query = ''
        clauseTables = ['SourceSource', ]
        if self.syncingapproved is not None:
            if len(query) > 0:
                query = query + ' AND '
            query = query + 'SourceSource.syncingapproved IS NOT NULL'
        if self.autotested is not None:
            if len(query) > 0:
                query = query + ' AND '
            query = query + 'SourceSource.autotested IS TRUE'
        if self.projecttext is not None:
            if len(query) > 0:
                query = query + ' AND '
            query = query + """SourceSource.product = Product.id AND
                               Product.project = Project.id AND
                               ( ( Project.title LIKE %%%s%% ) OR
                                 ( Project.shortdesc LIKE %%%s%% ) OR
                                 ( Project.description LIKE %%%s%% ) OR
                                 ( Product.title LIKE %%%s%% ) OR
                                 ( Product.shortdesc LIKE %%%s%% ) OR
                                 ( Product.description LIKE %%%s%% ) )
                                 """ % ( self.projecttext, self.projecttext,
                                         self.projecttext, self.projecttext,
                                         self.projecttext, self.projecttext )
            clauseTables.append('Project')
            clauseTables.append('Product')
        if len(query)==0:
            query = None
        self._resultset = SourceSource.select(query,
                clauseTables=clauseTables)

    def __iter__(self):
        if self._resultset is None:
            self.exec_query()
        for source in self._resultset:
            yield source


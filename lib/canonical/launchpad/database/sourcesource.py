"""Launchpad SourceSource Database Table Objects

Part of the Launchpad system.

(c) 2004 Canonical, Ltd.
"""

# Zope
from zope.interface import implements
from zope.component import getUtility

# SQL object
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from sqlobject import MultipleJoin, RelatedJoin, AND, LIKE
from canonical.database.sqlbase import SQLBase, quote

# Launchpad interfaces
# XXX: Daniel Debonzi 2004-11-25
# Why RCSTypeEnum is inside launchpad.interfaces?
from canonical.launchpad.interfaces import ISourceSource, \
    ISourceSourceAdmin, ISourceSourceSet, \
    RCSTypeEnum, RCSNames, IProductSet

from canonical.lp.dbschema import SourceSourceStatus

# tools
import datetime
from sets import Set
import logging

class SourceSource(SQLBase): 
    """SourceSource table"""

    implements (ISourceSource,
                ISourceSourceAdmin)
    
    _table = 'SourceSource'

    name = StringCol(dbName='name', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    product = ForeignKey(foreignKey='Product', dbName='product',
                         notNull=True)
    cvsroot = StringCol(dbName='cvsroot', default=None)
    cvsmodule = StringCol(dbName='cvsmodule', default=None)
    cvstarfile = ForeignKey(foreignKey='LibraryFileAlias',
                   dbName='cvstarfile', default=None)
    cvstarfileurl = StringCol(dbName='cvstarfileurl', default=None)
    cvsbranch = StringCol(dbName='cvsbranch', default=None)
    svnrepository = StringCol(dbName='svnrepository', default=None)
    # where are the tarballs released from this branch placed?
    releaseroot = StringCol(dbName='releaseroot', default=None)
    releaseverstyle = StringCol(dbName='releaseverstyle', default=None)
    # what glob is used for the releases ?
    releasefileglob = StringCol(dbName='releasefileglob', default=None)
    releaseparentbranch = ForeignKey(foreignKey='Branch',
                   dbName='releaseparentbranch', default=None)
    sourcepackage = ForeignKey(foreignKey='SourcePackage',
                   dbName='sourcepackage', default=None)
    branch = ForeignKey(foreignKey='Branch', dbName='branch', default=None)
    lastsynced = DateTimeCol(dbName='lastsynced', default=None)
    syncinterval = DateTimeCol(dbName='syncinterval', default=None)
    # WARNING: syncinterval column type is "interval", not "integer"
    # WARNING: make sure the data is what buildbot expects
    #IntCol('rcstype', dbName='rcstype', default=RCSTypeEnum.cvs,
    #       notNull=True),
    # FIXME: use 'RCSTypeEnum.cvs' rather than '1'
    rcstype = IntCol(dbName='rcstype', default=1,
               notNull=True)
    hosted = StringCol(dbName='hosted', default=None)
    upstreamname = StringCol(dbName='upstreamname', default=None)
    processingapproved = DateTimeCol(dbName='processingapproved',
                    notNull=False, default=None)
    syncingapproved = DateTimeCol(dbName='syncingapproved', notNull=False,
                    default=None)
    # For when Rob approves it
    newarchive = StringCol(dbName='newarchive')
    newbranchcategory = StringCol(dbName='newbranchcategory')
    newbranchbranch = StringCol(dbName='newbranchbranch')
    newbranchversion = StringCol(dbName='newbranchversion')
    # Temporary keybuk stuff
    packagedistro = StringCol(dbName='packagedistro', default=None)
    packagefiles_collapsed = StringCol(dbName='packagefiles_collapsed',
                default=None)
    owner = ForeignKey(foreignKey='Person', dbName='owner',
                   notNull=True)
    currentgpgkey = StringCol(dbName='currentgpgkey', default=None)
    fileidreference = StringCol(dbName='fileidreference', default=None)
    # canonical.lp.dbschema.ImportTestStatus
    autotested = IntCol(dbName='autotested', notNull=True, default=0)
    datestarted = DateTimeCol(dbName='datestarted', notNull=False,
        default=None)
    datefinished = DateTimeCol(dbName='datefinished', notNull=False,
        default=None)

    def namesReviewed(self):
        if not (self.product.reviewed and self.product.active):
            return False
        if self.product.project is not None:
            if not (self.product.project.reviewed and self.product.project.active):
                return False
        return True

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
        return self.product.name=="unassigned"

    def changeProduct(self, targetname):
        """change the product this sync belongs to to be 'product'"""
        assert (self.canChangeProduct())
        products = getUtility(IProductSet)
        self.product=products[targetname].id
        assert (self.product is not None)

    def needsReview(self):
        if not self.syncapproved and self.autotested:
            return True
        return False

    def _get_repository(self):
        if self.rcstype == RCSTypeEnum.cvs:
            return self.cvsroot
        elif self.rcstype == RCSTypeEnum.svn:
            return self.svnrepository
        elif self.rcstype == RCSTypeEnum.package:
            return
        else:
            logging.critical ("unhandled source rcs type: %s", self.rcstype)
            # FIXME!
            return None

    # Translate importd.Job.Job's instance variables to database columns by
    # creating some simple properties.  [Note that SQLObject turns _get_* and
    # _sets_* methods into properties automagically]
    #FIXME: buildbot should updated this on mirror completion.
    def _get_TYPE(self):
        # TODO: That is broken, that is cruft, and should be removed at
        # earliest convenience. -- 2005-02-17 David Allouche
 #       if self.lastsynced is None:
        if self.syncinterval is None or _interval_to_seconds(self.syncinterval) == 0:
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
        # OLD: The rest of this method can probably be deleted now.
        # NEW: it so can't, inheritance doesn't work here due to the RPC constraints.
        from importd.Job import CopyJob
        job = CopyJob()
        job.repository = str(self.repository)
        if self.syncingapproved is None:
            job.TYPE = 'import'
            if self.cvstarfileurl is not None and self.cvstarfileurl != "":
                job.repository = str(self.cvstarfileurl)
            job.frequency=0
        else:
            job.TYPE = 'sync'
            job.frequency = _interval_to_seconds(self.syncinterval)

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

        job.description = self.description
        job.sourceID = self.id

        job.releaseRoot = self.releaseroot
        job.releaseFileGlob = self.releasefileglob
        return job


def _interval_to_seconds(interval):
    try:
        return interval.days * 24 * 60 * 60 + interval.seconds
    except AttributeError:
        msg = "Failed to convert interval to seconds: %r" % (interval,)
        raise TypeError(msg)


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
        self.title = 'Bazaar Upstream Imports'

    def __getitem__(self, sourcesourcename):
        # XXX Strangely, the sourcesourcename appears to have been quoted
        # already. Quoting it again causes this query to break, though we
        # are not sure why.
        ss = SourceSource.select(SourceSource.q.name=="%s" % \
                                    sourcesourcename)
        return ss[0]

    def _querystr(self, ready=None, text=None, state=None):
        """Return a querystring and clauseTables for use in a search or a
        get or a query."""
        query = '1=1'
        clauseTables = Set()
        clauseTables.add('SourceSource')
        if ready is not None:
            if len(query) > 0:
                query = query + ' AND\n'
            query = query + """SourceSource.product = Product.id AND
                               Product.active IS TRUE AND
                               Product.reviewed IS TRUE AND
                             ( Product.project IS NULL OR
                             ( Product.project = Project.id AND
                               Project.active IS TRUE AND
                               Project.reviewed IS TRUE ) )
                               """
            clauseTables.add('Project')
            clauseTables.add('Product')
        elif state == SourceSourceStatus.TESTING:
            if len(query) > 0:
                query = query + ' AND '
            query = query + 'SourceSource.processingapproved IS NULL'
            query = query + ' AND '
            query = query + 'SourceSource.syncingapproved IS NULL'
            query = query + ' AND '
            query = query + 'SourceSource.autotested = 0'
        elif state == SourceSourceStatus.TESTFAILED:
            if len(query) > 0:
                query = query + ' AND '
            query = query + 'SourceSource.processingapproved IS NULL'
            query = query + ' AND '
            query = query + 'SourceSource.syncingapproved IS NULL'
            query = query + ' AND '
            query = query + 'SourceSource.autotested = 1'
        elif state == SourceSourceStatus.AUTOTESTED:
            if len(query) > 0:
                query = query + ' AND '
            query = query + 'SourceSource.autotested = 2'
        elif state == SourceSourceStatus.PROCESSING:
            if len(query) > 0:
                query = query + ' AND '
            query = query + 'SourceSource.processingapproved IS NOT NULL'
            query = query + ' AND '
            query = query + 'SourceSource.syncingapproved IS NULL'
        elif state == SourceSourceStatus.SYNCING:
            if len(query) > 0:
                query = query + ' AND '
            query = query + 'SourceSource.syncingapproved IS NOT NULL'
        elif state == SourceSourceStatus.STOPPED:
            pass
        if text:
            if len(query) > 0:
                query = query + ' AND '
            text = quote(text)
            if 'Product' not in clauseTables:
                query += 'SourceSource.product = Product.id AND '
                clauseTables.add('Product')
            query += 'Product.fti @@ ftq(%s) AND ' % text
            if 'Project' not in clauseTables:
                query = query + """
                             ( Product.project IS NULL OR
                               Product.project = Project.id ) AND
                               """
            query += " Project.fti @@ ftq(%s) " % text
            clauseTables.add('Project')
        return query, clauseTables

    def search(self, ready=None, 
                     text=None,
                     state=None,
                     start=None,
                     length=None):
        query, clauseTables = self._querystr(ready, text, state)
        return SourceSource.select(query, distinct=True,
                                   clauseTables=clauseTables)[start:length]
        

    def filter(self, sync=None, process=None, 
                     tested=None, text=None,
                     ready=None, assigned=None):
        query = ''
        clauseTables = Set()
        clauseTables.add('SourceSource')
        if ready is not None:
            if len(query) > 0:
                query = query + ' AND\n'
            query = query + """SourceSource.product = Product.id AND
                             ( Product.project IS NULL OR
                             ( Product.project = Project.id AND
                               Project.active IS TRUE AND
                               Project.reviewed IS TRUE ) ) AND
                               Product.active IS TRUE AND
                               Product.reviewed IS TRUE"""
            clauseTables.add('Project')
            clauseTables.add('Product')
        if sync is not None:
            if len(query) > 0:
                query = query + ' AND '
            query = query + 'SourceSource.syncingapproved IS NOT NULL'
        else:
            if len(query) > 0:
                query = query + ' AND '
            query = query + 'SourceSource.syncingapproved IS NULL'
        if process is not None:
            if len(query) > 0:
                query = query + ' AND '
            query = query + 'SourceSource.processingapproved IS NOT NULL'
        else:
            if len(query) > 0:
                query = query + ' AND '
            query = query + 'SourceSource.processingapproved IS NULL'
        if tested is not None:
            if len(query) > 0:
                query = query + ' AND '
            query = query + 'SourceSource.autotested = 2'
        if assigned is not None:
            if len(query) > 0:
                query = query + ' AND '                
            query = query + "Product.name != 'unassigned'"
            clauseTables.add('Product')
        else:
            if len(query) > 0:
                query = query + ' AND '                
            query = query + "Product.name = 'unassigned'"
            clauseTables.add('Product')
        if text is not None:
            if len(query) > 0:
                query = query + ' AND '
            if 'Project' not in clauseTables:
                query = query + """SourceSource.product = Product.id AND
                             ( Product.project IS NULL OR
                               Product.project = Project.id ) AND"""
            text = quote( '%' + text + '%' )
            query = query + """( ( Project.title ILIKE %s ) OR
                                 ( Project.shortdesc ILIKE %s ) OR
                                 ( Project.description ILIKE %s ) OR
                                 ( Product.title ILIKE %s ) OR
                                 ( Product.shortdesc ILIKE %s ) OR
                                 ( Product.description ILIKE %s ) )
                                 """ % ( text, text,
                                         text, text,
                                         text, text )
            clauseTables.add('Project')
            clauseTables.add('Product')
        if len(query)==0:
            query = None
        return SourceSource.select(query, distinct=True,
                                   clauseTables=clauseTables)



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
from canonical.launchpad.interfaces import ISourceSource, \
    ISourceSourceAdmin, ISourceSourceSet, IProductSet

from canonical.lp.dbschema import EnumCol
from canonical.lp.dbschema import ImportTestStatus
from canonical.lp.dbschema import SourceSourceStatus
from canonical.lp.dbschema import RevisionControlSystems
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
    branch = ForeignKey(foreignKey='Branch', dbName='branch', default=None)
    lastsynced = DateTimeCol(dbName='lastsynced', default=None)
    syncinterval = DateTimeCol(dbName='syncinterval', default=None)
    rcstype = EnumCol(dbName='rcstype',
                      default=RevisionControlSystems.CVS,
                      schema=RevisionControlSystems,
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
    autotested = EnumCol(dbName='autotested', notNull=True,
                         default=ImportTestStatus.NEW,
                         schema=ImportTestStatus)
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
        # XXX: Is that used anywhere but in buildJob? If not, that should
        # probably be moved to buildbot as well. -- David Allouche 2005-03-25
        if self.rcstype == RevisionControlSystems.CVS:
            return self.cvsroot
        elif self.rcstype == RevisionControlSystems.SVN:
            return self.svnrepository
        elif self.rcstype == RevisionControlSystems.PACKAGE:
            return None
        else:
            logging.critical ("unhandled source rcs type: %s", self.rcstype)
            # FIXME!
            return None

    def _get_package_files(self):
        # XXX: Not used anywhere but in buildJob. Should that be moved to
        # buildbot? -- David Allouche 2005-03-25
        if self.package_files_collapsed is None: return None
        return self.package_files_collapsed.split()

    def buildJob(self):
        """Create an importd job from the sourcesource data."""
        # XXX: Should that be moved to buildbot? -- David Allouche 2005-03-25
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
        RCSNames = {RevisionControlSystems.CVS: 'cvs',
                    RevisionControlSystems.SVN: 'svn',
                    RevisionControlSystems.ARCH: 'arch',
                    RevisionControlSystems.PACKAGE: 'package',
                    RevisionControlSystems.BITKEEPER: 'bitkeeper'}
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
    # XXX: only used in bulidJob, should probably moved to buildbot
    # -- David Allouche 2005-03-25
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
        ss = SourceSource.selectBy(name=sourcesourcename)
        return ss[0]

    def _querystr(self, ready=None, text=None, state=None):
        """Return a querystring and clauseTables for use in a search or a
        get or a query."""
        query = '1=1'
        clauseTables = Set()
        clauseTables.add('SourceSource')
        # deal with the cases which require project and product
        if ( ready is not None ) or text:
            if len(query) > 0:
                query = query + ' AND\n'
            query += "SourceSource.product = Product.id"
            if text:
                query += ' AND Product.fti @@ ftq(%s)' % quote(text)
            if ready is not None:
                query += ' AND '
                query += 'Product.active IS TRUE AND '
                query += 'Product.reviewed IS TRUE '
            query += ' AND '
            query += '( Product.project IS NULL OR '
            query += '( Product.project = Project.id '
            if text:
                query += ' AND Project.fti @@ ftq(%s) ' % quote(text)
            if ready is not None:
                query += ' AND '
                query += 'Project.active IS TRUE AND '
                query += 'Project.reviewed IS TRUE'
            query += ') )'
            clauseTables.add('Project')
            clauseTables.add('Product')
        # now just add filters on sourcesource
        if state == SourceSourceStatus.TESTING:
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
            query = query + 'SourceSource.processingapproved IS NULL'
            query = query + ' AND '
            query = query + 'SourceSource.syncingapproved IS NULL'
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
        return query, clauseTables

    def search(self, ready=None, 
                     text=None,
                     state=None,
                     start=None,
                     length=None):
        query, clauseTables = self._querystr(ready, text, state)
        return SourceSource.select(query, distinct=True,
                                   clauseTables=clauseTables)[start:length]
        

    # XXX Mark Shuttleworth 04/03/05 renamed to Xfilter to see if anything
    # breaks. If nothing has broken by end April feel free to remove
    # entirely.
    def Xfilter(self, sync=None, process=None, 
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



# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Launchpad SourceSource Database Table Objects"""

__metaclass__ = type
__all__ = ['XXXXSourceSource', 'XXXXSourceSourceSet']

import datetime
import sets
import logging

from zope.interface import implements

from sqlobject import DateTimeCol, ForeignKey, StringCol
from canonical.database.sqlbase import SQLBase, quote

from canonical.launchpad.interfaces import \
    ISourceSource, ISourceSourceAdmin, ISourceSourceSet

from canonical.lp.dbschema import EnumCol, ImportStatus, RevisionControlSystems


class XXXXSourceSource(SQLBase): 
    """SourceSource table"""

    implements (ISourceSource, ISourceSourceAdmin)

    _table = 'SourceSource'

    # canonical.lp.dbschema.ImportStatus
    importstatus = EnumCol(dbName='importstatus', notNull=True,
                           schema=ImportStatus, default=ImportStatus.TESTING)
    name = StringCol(default=None)
    title = StringCol(default=None)
    description = StringCol(default=None)
    cvsroot = StringCol(default=None)
    cvsmodule = StringCol(default=None)
    cvstarfile = ForeignKey(foreignKey='LibraryFileAlias',
                            dbName='cvstarfile', default=None)
    cvstarfileurl = StringCol(default=None)
    cvsbranch = StringCol(default=None)
    svnrepository = StringCol(default=None)
    # where are the tarballs released from this branch placed?
    releaseroot = StringCol(default=None)
    releaseverstyle = StringCol(default=None)
    releasefileglob = StringCol(default=None)
    releaseparentbranch = ForeignKey(foreignKey='Branch',
                                     dbName='releaseparentbranch', default=None)
    branch = ForeignKey(foreignKey='Branch', dbName='branch', default=None)
    lastsynced = DateTimeCol(default=None)
    syncinterval = DateTimeCol(default=None)
    rcstype = EnumCol(dbName='rcstype',
                      default=RevisionControlSystems.CVS,
                      schema=RevisionControlSystems,
                      notNull=True)
    hosted = StringCol(default=None)
    upstreamname = StringCol(default=None)
    processingapproved = DateTimeCol(default=None)
    syncingapproved = DateTimeCol(default=None)
    # For when Rob approves it
    newarchive = StringCol(default=None)
    newbranchcategory = StringCol(default=None)
    newbranchbranch = StringCol(default=None)
    newbranchversion = StringCol(default=None)
    # Temporary HORRIBLE HACK keybuk stuff
    packagedistro = StringCol(default=None)
    packagefiles_collapsed = StringCol(default=None)
    owner = ForeignKey(foreignKey='Person', dbName='owner',
                       notNull=True)
    currentgpgkey = StringCol(default=None)
    fileidreference = StringCol(default=None)
    dateautotested = DateTimeCol(default=None)
    datestarted = DateTimeCol(default=None)
    datefinished = DateTimeCol(default=None)
    productseries = ForeignKey(dbName='productseries',
                               foreignKey='ProductSeries',
                               notNull=True)

    # properties
    def product(self):
        return self.productseries.product
    product = property(product)

    def namesReviewed(self):
        if not (self.product.reviewed and self.product.active):
            return False
        if self.product.project is None:
            return True
        if self.product.project.reviewed and self.product.project.active:
            return True
        return False

    def certifyForSync(self):
        """Enable the sync for processing."""
        self.processingapproved = 'NOW'
        self.syncinterval = datetime.timedelta(1)
        self.importstatus = ImportStatus.PROCESSING

    def syncCertified(self):
        """Is the sync enabled?"""
        return self.processingapproved is not None

    def autoSyncEnabled(self):
        """Is the sync automatically scheduling?"""
        return self.importstatus == ImportStatus.SYNCING

    def enableAutoSync(self):
        """Enable autosyncing?"""
        self.syncingapproved = 'NOW'
        self.importstatus = ImportStatus.SYNCING

    def canChangeProductSeries(self):
        """Is this sync allowed to have its product series changed?"""
        return self.product.name == "unassigned"

    def changeProductSeries(self, series):
        """Change the productseries this sync belongs to."""
        assert (self.canChangeProductSeries())
        self.productseries = series

    def needsReview(self):
        return not self.syncapproved and self.dateautotested

    def _get_repository(self):
        # XXX: Is that used anywhere but in buildJob? If not, that should
        # probably be moved to buildbot as well. -- David Allouche 2005-03-25
        if self.rcstype == RevisionControlSystems.CVS:
            return self.cvsroot
        elif self.rcstype == RevisionControlSystems.SVN:
            return self.svnrepository
        else:
            logging.critical ("unhandled source rcs type: %s", self.rcstype)
            # FIXME!
            return None

    def _get_package_files(self):
        # XXX: Not used anywhere but in buildJob. Should that be moved to
        # buildbot? -- David Allouche 2005-03-25
        if self.package_files_collapsed is None:
            return None
        return self.package_files_collapsed.split()


class XXXXSourceSourceSet:
    """The set of SourceSource's."""
    implements(ISourceSourceSet)

    def __init__(self):
        self.title = 'Bazaar Upstream Imports'

    def __getitem__(self, sourcesourcename):
        ss = SourceSource.selectOneBy(name=sourcesourcename)
        if ss is None:
            raise KeyError(sourcesourcename)
        return ss

    def _querystr(self, ready=None, text=None, state=None):
        """Return a querystring and clauseTables for use in a search or a
        get or a query.
        """
        query = '1=1'
        clauseTables = sets.Set()
        clauseTables.add('SourceSource')
        # deal with the cases which require project and product
        if (ready is not None) or text:
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
        if state:
            if len(query) > 0:
                query += ' AND '
            query += 'SourceSource.importstatus = %d' % state
        return query, clauseTables

    def search(self, ready=None, 
                     text=None,
                     state=None,
                     start=None,
                     length=None):
        query, clauseTables = self._querystr(ready, text, state)
        return SourceSource.select(query, distinct=True,
                                   clauseTables=clauseTables)[start:length]

    # this is pedantic, to get every item individually, but it does allow
    # for making sure nothing gets passed in accidentally.
    def newSourceSource(self,
            owner=None,
            productseries=None,
            rcstype=None,
            cvsroot=None,
            cvsmodule=None,
            cvsbranch=None,
            cvstarfileurl=None,
            svnrepository=None,
            releaseroot=None,
            releaseverstyle=None,
            releasefileglob=None):
        return SourceSource(
            owner=owner,
            productseries=productseries,
            rcstype=rcstype,
            cvsroot=cvsroot,
            cvsmodule=cvsmodule,
            cvsbranch=cvsbranch,
            cvstarfileurl=cvstarfileurl,
            svnrepository=svnrepository,
            releaseroot=releaseroot,
            releaseverstyle=releaseverstyle,
            releasefileglob=releasefileglob)


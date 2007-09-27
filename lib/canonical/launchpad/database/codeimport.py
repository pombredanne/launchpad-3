# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Database classes including and related to CodeImport."""

__metaclass__ = type

__all__ = [
    'CodeImport',
    'CodeImportSet',
    ]

from sqlobject import ForeignKey, IntervalCol, StringCol, SQLObjectNotFound

from zope.component import getUtility
from zope.interface import implements

from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (cursor, SQLBase, sqlvalues)
from canonical.launchpad.database.productseries import ProductSeries
from canonical.launchpad.interfaces import (
    ICodeImport, ICodeImportSet, ILaunchpadCelebrities, NotFoundError,
    RevisionControlSystems)
from canonical.lp.dbschema import CodeImportReviewStatus


class CodeImport(SQLBase):
    """See ICodeImport."""

    implements(ICodeImport)
    _table = 'CodeImport'

    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    branch = ForeignKey(dbName='branch', foreignKey='Branch',
                        notNull=True)
    registrant = ForeignKey(dbName='registrant', foreignKey='Person',
                            notNull=True)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    assignee = ForeignKey(dbName='assignee', foreignKey='Person',
                          notNull=False, default=None)

    @property
    def product(self):
        """See `ICodeImport`."""
        return self.branch.product

    @property
    def series(self):
        """See `ICodeImport`."""
        return ProductSeries.selectOneBy(import_branch=self.branch)

    review_status = EnumCol(schema=CodeImportReviewStatus, notNull=True,
        default=CodeImportReviewStatus.NEW)

    rcs_type = EnumCol(schema=RevisionControlSystems,
        notNull=False, default=None)

    cvs_root = StringCol(default=None)

    cvs_module = StringCol(default=None)

    svn_branch_url = StringCol(default=None)

    date_last_successful = UtcDateTimeCol(default=None)
    update_interval = IntervalCol(default=None)


class CodeImportSet:
    """See `ICodeImportSet`."""

    implements(ICodeImportSet)

    def new(self, registrant, branch, rcs_type, svn_branch_url=None,
            cvs_root=None, cvs_module=None):
        """See `ICodeImportSet`."""
        assert branch.owner == getUtility(ILaunchpadCelebrities).vcs_imports
        if rcs_type == RevisionControlSystems.CVS:
            assert cvs_root is not None and cvs_module is not None
            assert svn_branch_url is None
        elif rcs_type == RevisionControlSystems.SVN:
            assert cvs_root is None and cvs_module is None
            assert svn_branch_url is not None
        else:
            raise AssertionError(
                "Don't know how to sanity check source details for unknown "
                "rcs_type %s"%rcs_type)
        return CodeImport(
            registrant=registrant, owner=registrant, branch=branch,
            rcs_type=rcs_type, svn_branch_url=svn_branch_url,
            cvs_root=cvs_root, cvs_module=cvs_module)

    # XXX: DavidAllouche 2007-07-05:
    # newWithId is only needed for code-import-sync-script. This method
    # should be removed after the transition to the new code import system is
    # complete.

    def newWithId(self, id, registrant, branch, rcs_type, svn_branch_url=None,
            cvs_root=None, cvs_module=None):
        """See `ICodeImportSet`."""
        assert branch.owner == getUtility(ILaunchpadCelebrities).vcs_imports
        if rcs_type == RevisionControlSystems.CVS:
            assert cvs_root is not None and cvs_module is not None
            assert svn_branch_url is None
        elif rcs_type == RevisionControlSystems.SVN:
            assert cvs_root is None and cvs_module is None
            assert svn_branch_url is not None
        else:
            raise AssertionError(
                "Don't know how to sanity check source details for unknown "
                "rcs_type %s"%rcs_type)
        cur = cursor()
        cur.execute("""
            SELECT setval('codeimport_id_seq', GREATEST(%s, (
                SELECT last_value from codeimport_id_seq)));"""
            % sqlvalues(id))
        assert len(cur.fetchall()) == 1
        return CodeImport(
            id=id, registrant=registrant, owner=registrant, branch=branch,
            rcs_type=rcs_type, svn_branch_url=svn_branch_url,
            cvs_root=cvs_root, cvs_module=cvs_module)

    def delete(self, id):
        """See `ICodeImportSet`."""
        CodeImport.delete(id)

    def getAll(self):
        """See `ICodeImportSet`."""
        return CodeImport.select()

    def get(self, id):
        """See `ICodeImportSet`."""
        try:
            return CodeImport.get(id)
        except SQLObjectNotFound:
            raise NotFoundError(id)

    def getByBranch(self, branch):
        """See `ICodeImportSet`."""
        return CodeImport.selectOneBy(branch=branch)

    def search(self, review_status):
        """See `ICodeImportSet`."""
        return CodeImport.selectBy(review_status=review_status.value)

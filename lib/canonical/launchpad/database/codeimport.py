# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Database classes including and related to CodeImport."""

__metaclass__ = type

__all__ = [
    'CodeImport',
    'CodeImportSet',
    ]

from datetime import timedelta

from sqlobject import ForeignKey, IntervalCol, StringCol, SQLObjectNotFound
from zope.component import getUtility
from zope.interface import implements

from canonical.config import config
from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import (cursor, SQLBase, sqlvalues)
from canonical.launchpad.database.productseries import ProductSeries
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, NotFoundError,
    ICodeImportEventSet, RevisionControlSystems,
    ICodeImport, ICodeImportSet)
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

    @property
    def effective_update_interval(self):
        """See `ICodeImport`."""
        if self.update_interval is not None:
            return self.update_interval
        default_interval_dict = {
            RevisionControlSystems.CVS:
                config.codeimport.default_interval_cvs,
            RevisionControlSystems.SVN:
                config.codeimport.default_interval_subversion}
        seconds = default_interval_dict[self.rcs_type]
        return timedelta(seconds=seconds)


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
        code_import = CodeImport(
            registrant=registrant, owner=registrant, branch=branch,
            rcs_type=rcs_type, svn_branch_url=svn_branch_url,
            cvs_root=cvs_root, cvs_module=cvs_module)
        getUtility(ICodeImportEventSet).newCreate(code_import, registrant)
        return code_import

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
        code_import = CodeImport(
            id=id, registrant=registrant, owner=registrant, branch=branch,
            rcs_type=rcs_type, svn_branch_url=svn_branch_url,
            cvs_root=cvs_root, cvs_module=cvs_module)
        getUtility(ICodeImportEventSet).newCreate(code_import, registrant)
        return code_import

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

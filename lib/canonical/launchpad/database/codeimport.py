# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Database classes including and related to CodeImport."""

__metaclass__ = type

__all__ = [
    'CodeImport',
    'CodeImportSet',
    ]

from datetime import timedelta

from sqlobject import (
    ForeignKey, IntervalCol, SingleJoin, StringCol, SQLObjectNotFound)
from zope.component import getUtility
from zope.event import notify
from zope.interface import implements

from canonical.config import config
from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.database.productseries import ProductSeries
from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.interfaces import (
    BranchCreationException, BranchType, CodeImportReviewStatus, IBranchSet,
    ICodeImport, ICodeImportEventSet, ICodeImportSet,
    ILaunchpadCelebrities, NotFoundError, RevisionControlSystems)
from canonical.launchpad.validators.person import public_person_validator


class CodeImport(SQLBase):
    """See ICodeImport."""

    implements(ICodeImport)
    _table = 'CodeImport'
    _defaultOrder = ['id']

    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    branch = ForeignKey(dbName='branch', foreignKey='Branch',
                        notNull=True)
    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person',
        validator=public_person_validator, notNull=True)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        validator=public_person_validator, notNull=True)
    assignee = ForeignKey(
        dbName='assignee', foreignKey='Person',
        validator=public_person_validator, notNull=False, default=None)

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

    import_job = SingleJoin('CodeImportJob', joinColumn='code_importID')

    def updateFromData(self, data, user):
        """See `ICodeImport`."""
        event_set = getUtility(ICodeImportEventSet)
        token = event_set.beginModify(self)
        for name, value in data.items():
            setattr(self, name, value)
        event_set.newModify(self, user, token)


class CodeImportSet:
    """See `ICodeImportSet`."""

    implements(ICodeImportSet)

    def new(self, registrant, product, branch_name, rcs_type,
            svn_branch_url=None, cvs_root=None, cvs_module=None,
            review_status=None):
        """See `ICodeImportSet`."""
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
        if review_status is None:
            review_status = CodeImportReviewStatus.NEW
        # Create the branch for the CodeImport.
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        branch_set = getUtility(IBranchSet)
        if branch_set.getBranch(vcs_imports, product, branch_name):
            raise BranchCreationException(
                "A branch already exists for the %s project owned by "
                "vcs-imports with the name %s" % (product.name, branch_name))
        import_branch = branch_set.new(
            branch_type=BranchType.IMPORTED, name=branch_name,
            creator=vcs_imports, owner=vcs_imports,
            product=product, url=None)

        code_import = CodeImport(
            registrant=registrant, owner=registrant, branch=import_branch,
            rcs_type=rcs_type, svn_branch_url=svn_branch_url,
            cvs_root=cvs_root, cvs_module=cvs_module,
            review_status=review_status)

        getUtility(ICodeImportEventSet).newCreate(code_import, registrant)
        notify(SQLObjectCreatedEvent(code_import))
        return code_import

    def delete(self, code_import):
        """See `ICodeImportSet`."""
        from canonical.launchpad.database import CodeImportJob
        if code_import.import_job is not None:
            CodeImportJob.delete(code_import.import_job.id)
        CodeImport.delete(code_import.id)

    def getAll(self):
        """See `ICodeImportSet`."""
        return CodeImport.select()

    def get(self, id):
        """See `ICodeImportSet`."""
        try:
            return CodeImport.get(id)
        except SQLObjectNotFound:
            raise NotFoundError(id)

    def getByCVSDetails(self, cvs_root, cvs_module):
        """See `ICodeImportSet`."""
        return CodeImport.selectOneBy(
            cvs_root=cvs_root, cvs_module=cvs_module)

    def getBySVNDetails(self, svn_branch_url):
        """See `ICodeImportSet`."""
        return CodeImport.selectOneBy(svn_branch_url=svn_branch_url)

    def getByBranch(self, branch):
        """See `ICodeImportSet`."""
        return CodeImport.selectOneBy(branch=branch)

    def search(self, review_status):
        """See `ICodeImportSet`."""
        return CodeImport.selectBy(review_status=review_status.value)

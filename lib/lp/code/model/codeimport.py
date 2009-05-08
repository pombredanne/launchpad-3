# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""Database classes including and related to CodeImport."""

__metaclass__ = type

__all__ = [
    'CodeImport',
    'CodeImportSet',
    ]

from datetime import timedelta

from storm.expr import Select, And, Func
from storm.locals import Store
from storm.references import Reference
from sqlobject import (
    ForeignKey, IntervalCol, StringCol, SQLMultipleJoin,
    SQLObjectNotFound)
from zope.component import getUtility
from zope.event import notify
from zope.interface import implements

from lazr.lifecycle.event import ObjectCreatedEvent

from canonical.config import config
from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, quote, sqlvalues
from lp.code.model.codeimportjob import CodeImportJobWorkflow
from lp.registry.model.productseries import ProductSeries
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.webapp.interfaces import NotFoundError
from lp.code.interfaces.branch import BranchType
from lp.code.interfaces.codeimport import (
    CodeImportReviewStatus, ICodeImport, ICodeImportSet)
from lp.code.interfaces.codeimportevent import ICodeImportEventSet
from lp.code.interfaces.codeimportjob import CodeImportJobState
from lp.code.interfaces.branchnamespace import (
    get_branch_namespace)
from lp.code.interfaces.codeimport import RevisionControlSystems
from lp.code.model.codeimportresult import (
    CodeImportResult, CodeImportResultStatus)
from canonical.launchpad.mailout.codeimport import code_import_updated
from lp.registry.interfaces.person import validate_public_person


class CodeImport(SQLBase):
    """See `ICodeImport`."""

    implements(ICodeImport)
    _table = 'CodeImport'
    _defaultOrder = ['id']

    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)
    branch = ForeignKey(dbName='branch', foreignKey='Branch',
                        notNull=True)
    registrant = ForeignKey(
        dbName='registrant', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    assignee = ForeignKey(
        dbName='assignee', foreignKey='Person',
        storm_validator=validate_public_person, notNull=False, default=None)

    @property
    def product(self):
        """See `ICodeImport`."""
        return self.branch.product

    @property
    def series(self):
        """See `ICodeImport`."""
        return ProductSeries.selectOneBy(branch=self.branch)

    review_status = EnumCol(schema=CodeImportReviewStatus, notNull=True,
        default=CodeImportReviewStatus.NEW)

    rcs_type = EnumCol(schema=RevisionControlSystems,
        notNull=False, default=None)

    cvs_root = StringCol(default=None)

    cvs_module = StringCol(default=None)

    svn_branch_url = StringCol(default=None)

    git_repo_url = StringCol(default=None)

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
                config.codeimport.default_interval_subversion,
            RevisionControlSystems.GIT:
                config.codeimport.default_interval_git,
            }
        seconds = default_interval_dict[self.rcs_type]
        return timedelta(seconds=seconds)

    import_job = Reference("<primary key>", "CodeImportJob.code_importID",
                           on_remote=True)

    def getImportDetailsForDisplay(self):
        """See `ICodeImport`."""
        assert self.rcs_type is not None, (
            "Only makes sense for series with import details set.")
        if self.rcs_type == RevisionControlSystems.CVS:
            return '%s %s' % (self.cvs_root, self.cvs_module)
        elif self.rcs_type == RevisionControlSystems.SVN:
            return self.svn_branch_url
        else:
            raise AssertionError(
                'Unknown rcs type: %s'% self.rcs_type.title)

    def _removeJob(self):
        """If there is a pending job, remove it."""
        job = self.import_job
        if job is not None:
            if job.state == CodeImportJobState.PENDING:
                CodeImportJobWorkflow().deletePendingJob(self)
            else:
                # XXX thumper 2008-03-19
                # When we have job killing, we might want to kill a running
                # job.
                pass
        else:
            # No job, so nothing to do.
            pass

    results = SQLMultipleJoin(
        'CodeImportResult', joinColumn='code_import',
        orderBy=['-date_job_started'])

    def changeDetails(self, data, user):
        """See `ICodeImport`."""
        if 'review_status' in data:
            raise AssertionError(
                'changeDetails cannot be used to change review_status.')
        modify_event = self.updateFromData(data, user)
        if modify_event is not None:
            code_import_updated(modify_event)
            return True
        else:
            return False

    @property
    def consecutive_failure_count(self):
        """See `ICodeImport`."""
        last_success = Func(
            "coalesce",
            Select(
                CodeImportResult.id,
                And(CodeImportResult.status == CodeImportResultStatus.SUCCESS,
                    CodeImportResult.code_import == self),
                order_by=CodeImportResult.id,
                limit=1),
            0)
        return Store.of(self).find(
            CodeImportResult,
            CodeImportResult.code_import == self,
            CodeImportResult.id > last_success).count()

    def updateFromData(self, data, user):
        """See `ICodeImport`."""
        event_set = getUtility(ICodeImportEventSet)
        new_whiteboard = None
        if 'whiteboard' in data:
            whiteboard = data.pop('whiteboard')
            if whiteboard != self.branch.whiteboard:
                if whiteboard is None:
                    new_whiteboard = ''
                else:
                    new_whiteboard = whiteboard
                self.branch.whiteboard = whiteboard
        token = event_set.beginModify(self)
        for name, value in data.items():
            setattr(self, name, value)
        if 'review_status' in data:
            if data['review_status'] == CodeImportReviewStatus.REVIEWED:
                CodeImportJobWorkflow().newJob(self)
            else:
                self._removeJob()
        event = event_set.newModify(self, user, token)
        if event is not None or new_whiteboard is not None:
            code_import_updated(self, event, new_whiteboard, user)
        return event

    def __repr__(self):
        return "<CodeImport for %s>" % self.branch.unique_name


class CodeImportSet:
    """See `ICodeImportSet`."""

    implements(ICodeImportSet)

    def new(self, registrant, product, branch_name, rcs_type,
            svn_branch_url=None, cvs_root=None, cvs_module=None,
            review_status=None, git_repo_url=None):
        """See `ICodeImportSet`."""
        if rcs_type == RevisionControlSystems.CVS:
            assert cvs_root is not None and cvs_module is not None
            assert svn_branch_url is None
            assert git_repo_url is None
        elif rcs_type == RevisionControlSystems.SVN:
            assert cvs_root is None and cvs_module is None
            assert svn_branch_url is not None
            assert git_repo_url is None
        elif rcs_type == RevisionControlSystems.GIT:
            assert cvs_root is None and cvs_module is None
            assert svn_branch_url is None
            assert git_repo_url is not None
        else:
            raise AssertionError(
                "Don't know how to sanity check source details for unknown "
                "rcs_type %s"%rcs_type)
        if review_status is None:
            review_status = CodeImportReviewStatus.NEW
        # Create the branch for the CodeImport.
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        namespace = get_branch_namespace(vcs_imports, product)
        import_branch = namespace.createBranch(
            branch_type=BranchType.IMPORTED, name=branch_name,
            registrant=vcs_imports)

        code_import = CodeImport(
            registrant=registrant, owner=registrant, branch=import_branch,
            rcs_type=rcs_type, svn_branch_url=svn_branch_url,
            cvs_root=cvs_root, cvs_module=cvs_module,
            review_status=review_status, git_repo_url=git_repo_url)

        getUtility(ICodeImportEventSet).newCreate(code_import, registrant)
        notify(ObjectCreatedEvent(code_import))

        # If created in the reviewed state, create a job.
        if review_status == CodeImportReviewStatus.REVIEWED:
            CodeImportJobWorkflow().newJob(code_import)

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

    def getActiveImports(self, text=None):
        """See `ICodeImportSet`."""
        query = self.composeQueryString(text)
        return CodeImport.select(
            query, orderBy=['product.name', 'branch.name'],
            clauseTables=['Product', 'Branch'])

    def composeQueryString(self, text=None):
        """Build SQL "where" clause for `CodeImport` search.

        :param text: Text to search for in the product and project titles and
            descriptions.
        """
        conditions = [
            "date_last_successful IS NOT NULL",
            "review_status=%s" % sqlvalues(CodeImportReviewStatus.REVIEWED),
            "CodeImport.branch = Branch.id",
            "Branch.product = Product.id",
            ]
        if text == u'':
            text = None

        # First filter on text, if supplied.
        if text is not None:
            conditions.append("""
                ((Project.fti @@ ftq(%s) AND Product.project IS NOT NULL) OR
                Product.fti @@ ftq(%s))""" % (quote(text), quote(text)))

        # Exclude deactivated products.
        conditions.append('Product.active IS TRUE')

        # Exclude deactivated projects, too.
        conditions.append(
            "((Product.project = Project.id AND Project.active) OR"
            " Product.project IS NULL)")

        # And build the query.
        query = " AND ".join(conditions)
        return """
            codeimport.id IN
            (SELECT codeimport.id FROM codeimport, branch, product, project
             WHERE %s)
            AND codeimport.branch = branch.id
            AND branch.product = product.id""" % query

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

    def getByGitDetails(self, git_repo_url):
        """See `ICodeImportSet`."""
        return CodeImport.selectOneBy(git_repo_url=git_repo_url)

    def getBySVNDetails(self, svn_branch_url):
        """See `ICodeImportSet`."""
        return CodeImport.selectOneBy(svn_branch_url=svn_branch_url)

    def getByBranch(self, branch):
        """See `ICodeImportSet`."""
        return CodeImport.selectOneBy(branch=branch)

    def search(self, review_status):
        """See `ICodeImportSet`."""
        return CodeImport.selectBy(review_status=review_status)

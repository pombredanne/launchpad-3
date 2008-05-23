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
    ForeignKey, IntervalCol, SingleJoin, StringCol, SQLMultipleJoin,
    SQLObjectNotFound)
from zope.component import getUtility
from zope.event import notify
from zope.interface import implements

from canonical.config import config
from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.database.codeimportjob import CodeImportJobWorkflow
from canonical.launchpad.database.productseries import ProductSeries
from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.interfaces import (
    BranchCreationException, BranchType, CodeImportJobState,
    CodeImportReviewStatus, IBranchSet, ICodeImport, ICodeImportEventSet,
    ICodeImportSet, ILaunchpadCelebrities, ImportStatus, NotFoundError,
    RevisionControlSystems)
from canonical.launchpad.mailout.codeimport import code_import_status_updated
from canonical.launchpad.validators.person import public_person_validator


class _ProductSeriesCodeImport(SQLBase):
    """A table linking CodeImports to the ProductSeries their data came from.
    """
    # XXX: MichaelHudson 2008-05-20, bug=232076: This table is only necessary
    # for the transition from the old to the new code import system, and
    # should be deleted after that process is done.

    _table = 'ProductSeriesCodeImport'

    productseries = ForeignKey(
        dbName='productseries', foreignKey='ProductSeries', notNull=True)
    codeimport = ForeignKey(
        dbName='codeimport', foreignKey='CodeImport', notNull=True)


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

    @property
    def source_product_series(self):
        """See `ICodeImport`."""
        # XXX: MichaelHudson 2008-05-20, bug=232076: This property is
        # only necessary for the transition from the old to the new
        # code import system, and should be deleted after that process
        # is done.
        pair = _ProductSeriesCodeImport.selectOneBy(
            codeimport=self)
        if pair is not None:
            return pair.productseries
        else:
            return None

    def approve(self, data, user):
        """See `ICodeImport`."""
        if self.review_status == CodeImportReviewStatus.REVIEWED:
            raise AssertionError('Review status is already reviewed.')
        self._setStatusAndEmail(data, user, CodeImportReviewStatus.REVIEWED)
        CodeImportJobWorkflow().newJob(self)

    def suspend(self, data, user):
        """See `ICodeImport`."""
        if self.review_status == CodeImportReviewStatus.SUSPENDED:
            raise AssertionError('Review status is already suspended.')
        self._setStatusAndEmail(data, user, CodeImportReviewStatus.SUSPENDED)
        self._removeJob()

    def invalidate(self, data, user):
        """See `ICodeImport`."""
        if self.review_status == CodeImportReviewStatus.INVALID:
            raise AssertionError('Review status is already invalid.')
        self._setStatusAndEmail(data, user, CodeImportReviewStatus.INVALID)
        self._removeJob()

    def _setStatusAndEmail(self, data, user, status):
        """Update the review_status and email interested parties."""
        data['review_status'] = status
        self.updateFromData(data, user)
        code_import_status_updated(self, user)

    def updateFromData(self, data, user):
        """See `ICodeImport`."""
        event_set = getUtility(ICodeImportEventSet)
        token = event_set.beginModify(self)
        for name, value in data.items():
            setattr(self, name, value)
        event_set.newModify(self, user, token)

    def __repr__(self):
        return "<CodeImport for %s>" % self.branch.unique_name


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
            registrant=vcs_imports, owner=vcs_imports,
            product=product, url=None)

        code_import = CodeImport(
            registrant=registrant, owner=registrant, branch=import_branch,
            rcs_type=rcs_type, svn_branch_url=svn_branch_url,
            cvs_root=cvs_root, cvs_module=cvs_module,
            review_status=review_status)

        getUtility(ICodeImportEventSet).newCreate(code_import, registrant)
        notify(SQLObjectCreatedEvent(code_import))

        # If created in the reviewed state, create a job.
        if review_status == CodeImportReviewStatus.REVIEWED:
            CodeImportJobWorkflow().newJob(code_import)

        return code_import

    def _reviewStatusFromImportStatus(self, import_status):
        """The value for review_status corresponding to `import_status`.
        """
        # XXX: MichaelHudson 2008-05-20, bug=232076: This method is only
        # necessary for the transition from the old to the new code import
        # system, and should be deleted after that process is done.
        if import_status in (ImportStatus.TESTING, ImportStatus.AUTOTESTED):
            review_status = CodeImportReviewStatus.NEW
        elif import_status in (ImportStatus.PROCESSING, ImportStatus.SYNCING):
            review_status = CodeImportReviewStatus.REVIEWED
        elif import_status == ImportStatus.STOPPED:
            review_status = CodeImportReviewStatus.SUSPENDED
        else:
            raise AssertionError(
                "This import status should not produce a code import: %s"
                % import_status.name)
        return review_status

    def _dateLastSuccessfulFromProductSeries(self, series):
        """The value for date_last_successful for the ProductSeries `series`.
        """
        # XXX: MichaelHudson 2008-05-20, bug=232076: This method is only
        # necessary for the transition from the old to the new code import
        # system, and should be deleted after that process is done.
        if series.importstatus in (ImportStatus.SYNCING,
                                   ImportStatus.STOPPED):
            last_successful = series.datelastsynced
        elif series.importstatus in (ImportStatus.TESTING,
                                     ImportStatus.AUTOTESTED,
                                     ImportStatus.PROCESSING):
            last_successful = None
        else:
            raise AssertionError(
                "This import status should not produce a code import: %s"
                % series.importstatus.name)
        return last_successful

    def _dateCreatedFromProductSeries(self, series):
        """Make up a date_created field for the new code import.

        As the entering of import details is not treated like an event in the
        old code import system, this requires a touch of creativity.  What we
        do is return the longest ago of whichever of
        series.dateprocessapproved and series.dateautotested have been set, or
        DEFAULT if neither have.
        """
        # XXX: MichaelHudson 2008-05-20, bug=232076: This method is only
        # necessary for the transition from the old to the new code import
        # system, and should be deleted after that process is done.
        candidates = [date for date in (series.dateprocessapproved,
                                        series.dateautotested)
                      if date is not None]
        if candidates:
            return min(candidates)
        else:
            return DEFAULT

    def _updateIntervalFromProductSeries(self, series):
        """The value for 'update_interval' from `series`.

        If the series has a non-default syncinterval, return that.  Otherwise
        return None.
        """
        if series.rcstype == RevisionControlSystems.CVS and \
               series.syncinterval != timedelta(hours=12):
            return series.syncinterval
        elif series.rcstype == RevisionControlSystems.SVN and \
               series.syncinterval != timedelta(hours=6):
            return series.syncinterval
        else:
            return None

    def newFromProductSeries(self, product_series):
        """See `ICodeImportSet`."""
        # XXX: MichaelHudson 2008-05-20, bug=232076: This method is only
        # necessary for the transition from the old to the new code import
        # system, and should be deleted after that process is done.
        date_created = self._dateCreatedFromProductSeries(product_series)

        _vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports

        if product_series.import_branch is not None:
            branch = product_series.import_branch
        else:
            # Note that it is possible, although unlikely, for there to be a
            # branch with this name already, so this can raise
            # BranchCreationException.
            branch = getUtility(IBranchSet).new(
                branch_type=BranchType.IMPORTED, name=product_series.name,
                registrant=_vcs_imports, owner=_vcs_imports,
                product=product_series.product, url=None)

        registrant = _vcs_imports
        owner = _vcs_imports
        assignee = None
        review_status = self._reviewStatusFromImportStatus(
            product_series.importstatus)

        rcs_type = product_series.rcstype
        cvs_root = product_series.cvsroot
        cvs_module = product_series.cvsmodule
        svn_branch_url = product_series.svnrepository
        date_last_successful = self._dateLastSuccessfulFromProductSeries(
            product_series)
        update_interval = self._updateIntervalFromProductSeries(
            product_series)

        code_import = CodeImport(
            date_created=date_created, branch=branch, registrant=registrant,
            owner=owner, assignee=assignee, rcs_type=rcs_type,
            svn_branch_url=svn_branch_url, cvs_root=cvs_root,
            cvs_module=cvs_module, review_status=review_status,
            date_last_successful=date_last_successful,
            update_interval=update_interval)

        product_series.markStopped()

        if product_series.import_branch:
            if product_series.user_branch is None:
                # Rather than give ~vcs-imports the right to set the
                # user_branch on any series, it seems cleaner to avoid the
                # security machinery in this one location.
                from zope.security.proxy import removeSecurityProxy
                removeSecurityProxy(product_series).user_branch = \
                    product_series.import_branch
            product_series.import_branch = None

        # If created in the reviewed state, create a job.
        if review_status == CodeImportReviewStatus.REVIEWED:
            # This will more-or-less by chance create a job that is due now,
            # which is fine.
            CodeImportJobWorkflow().newJob(code_import)

        # We deliberately don't fire an object created event or call
        # newCreate.

        # Record the link between the new code import and the product series
        # it came from.
        _ProductSeriesCodeImport(
            codeimport=code_import, productseries=product_series)

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

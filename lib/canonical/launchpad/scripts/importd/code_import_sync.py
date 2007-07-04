# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Populate and update the CodeImport table from the ProductSeries table.

This module is the back-end for cronscripts/code-import-sync.py.
"""

__metaclass__ = type
__all__ = ['CodeImportSync']


import psycopg
from zope.component import getUtility

from canonical.lp.dbschema import CodeImportReviewStatus, ImportStatus
from canonical.launchpad.interfaces import (
    IBranchSet, ICodeImportSet, ILaunchpadCelebrities, IProductSeriesSet)
from canonical.launchpad.webapp import canonical_url


class CodeImportSync:
    """Populate and update the CodeImport table from the ProductSeries table.
    """

    def __init__(self, logger, txn):
        self.logger = logger
        self.txn = txn

    def runAndCommit(self):
        """Entry point method for the script runner."""
        self.run()
        self.txn.commit()

    def run(self):
        """Synchronize the CodeImport table with the ProductSeries table."""

        # Get all relevant ProductSeries, and all CodeImports. We will need
        # them later for set arithmetic. So we may as well use the complete
        # lists for everything.
        import_series_list = list(self.getImportSeries())
        code_imports_map = dict(
            (code_import.id, code_import)
            for code_import in getUtility(ICodeImportSet).getAll())

        # Create or update CodeImports associated to valid ProductSeries.
        for series in import_series_list:
            code_import = code_imports_map.get(series.id)
            if code_import is None:
                self.createCodeImport(series)
            else:
                self.updateCodeImport(series, code_import)

        # Delete CodeImports not associated to any valid ProductSeries.
        import_series_ids = set(series.id for series in import_series_list)
        code_import_ids = set(code_imports_map.iterkeys())
        for orphaned_id in code_import_ids.difference(import_series_ids):
            self.deleteOrphanedCodeImport(orphaned_id)

    def getImportSeries(self):
        """Iterate over ProductSeries for which we want to have a CodeImport.

        This is any series where importstatus is TESTING, AUTOTESTED,
        PROCESSING, SYNCING or STOPPED.

        Series where importstatus is DONTSYNC or TESTFAILED are ignored.
        """
        series_iterator = getUtility(IProductSeriesSet).search(forimport=True)
        for series in series_iterator:
            if series.importstatus in (ImportStatus.DONTSYNC,
                                       ImportStatus.TESTFAILED):
                continue
            elif series.importstatus in (ImportStatus.TESTING,
                                         ImportStatus.AUTOTESTED,
                                         ImportStatus.PROCESSING,
                                         ImportStatus.SYNCING,
                                         ImportStatus.STOPPED):
                # TODO: filter out non-main branches
                yield series
            else:
                assert series.importstatus is not None
                raise AssertionError(
                    "Unknown importstatus: %s", series.importstatus.name)

    def reviewStatusFromImportStatus(self, import_status):
        """Return the CodeImportReviewStatus value corresponding to the given
        ImportStatus value.
        """
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

    def dateLastSuccessfulFromProductSeries(self, series):
        """Return the date_last_successful for the code import associated to
        the given ProductSeries.
        """
        if series.importstatus in (ImportStatus.SYNCING, ImportStatus.STOPPED):
            last_successful = series.datelastsynced

            # This invariant is depended on by the logic in updateCodeImport
            # that decides if we need to create a new branch for an exiting
            # CodeImport.
            assert last_successful is not None

        elif series.importstatus in (ImportStatus.TESTING,
                                     ImportStatus.AUTOTESTED,
                                     ImportStatus.PROCESSING):
            last_successful = None
        else:
            raise AssertionError(
                "This import status should not produce a code import: %s"
                % series.importstatus.name)
        return last_successful

    def createCodeImport(self, series):
        """Create the CodeImport object corresponding to the given
        ProductSeries.

        :param series: a ProductSeries associated to a code import.
        :return: the created CodeImport, or None if there was a branch name
            conflict.

        :precondition: The CodeImport object corresponding to `series` does
            already exist in the database.
        :postcondition: The CodeImport object corresponding to `series` exists
            in the database and is up to date.
        """
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports

        # Get a branch to attach the new CodeImport to.
        if series.import_branch is not None:
            # Use the ProductSeries import_branch if it set.
            branch = series.import_branch
        else:
            # Otherwise, try to create an import branch.
            branch = self.createNewImportBranch(series)
            if branch is None:
                # A branch name conflict occured.
                return
        # Given the branch, we can create the CodeImport.
        code_import = getUtility(ICodeImportSet).newWithId(
            series.id, vcs_imports, branch, series.rcstype,
            svn_branch_url=series.svnrepository,
            cvs_root=series.cvsroot, cvs_module=series.cvsmodule)
        review_status = self.reviewStatusFromImportStatus(series.importstatus)
        code_import.review_status = review_status
        date_last_successful = self.dateLastSuccessfulFromProductSeries(series)
        code_import.date_last_successful = date_last_successful
        return code_import

    def updateCodeImport(self, series, code_import):
        """Update `code_import` to match `series`.

        :param series: a ProductSeries associated to a code import.
        :param code_import: The CodeImport corresponding to `series`.
        :postcondition: `code_import` is up to date with `series`.
        """
        assert (series.import_branch is None
                or code_import.branch == series.import_branch)

        # If the previous date_last_successful was not NULL, and the new one is
        # NULL, that means we are doing a re-import. So we must use a new
        # branch.
        date_last_successful = self.dateLastSuccessfulFromProductSeries(series)
        if (code_import.date_last_successful is not None
                and date_last_successful is None):
            new_branch = self.createNewImportBranch(series)
            if new_branch is None:
                # A branch name conflict occured.
                return
            code_import.branch = new_branch
        code_import.date_last_successful = date_last_successful

        code_import.rcs_type = series.rcstype
        code_import.cvs_root = series.cvsroot
        code_import.cvs_module = series.cvsmodule
        assert series.cvsbranch is None or series.cvsbranch == 'MAIN'
        code_import.svn_branch_url = series.svnrepository
        review_status = self.reviewStatusFromImportStatus(series.importstatus)
        code_import.review_status = review_status

    def createNewImportBranch(self, series):
        """Create a new branch for the CodeImport associated to `series`.

        :param: an import ProductSeries.
        :return: an import branch, or None if a branch name conflict occured.
        """
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        unique_name = '~%s/%s/%s' % (
            vcs_imports.name, series.product.name, series.name)
        branch_set = getUtility(IBranchSet)
        conflict_branch = branch_set.getByUniqueName(unique_name)
        if conflict_branch is not None:
            # If there is already an import branch by this name, it should
            # probably be renamed or deleted.
            self.logger.error("Branch name conflict: %s",
                canonical_url(conflict_branch))
            return None
        branch = getUtility(IBranchSet).new(
            series.name, vcs_imports, series.product, None, None)
        return branch

    def deleteOrphanedCodeImport(self, code_import_id):
        """Delete a CodeImport object that is no longer associated to an import
        product series.

        :param code_import_id: database id of a CodeImport.
        """
        code_import = getUtility(ICodeImportSet).get(code_import_id)
        getUtility(ICodeImportSet).delete(code_import_id)
        self.logger.warning(
            "Branch was orphaned, you may want to delete it: %s",
            canonical_url(code_import.branch))


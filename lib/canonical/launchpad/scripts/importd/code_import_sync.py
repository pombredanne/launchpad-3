# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Populate and update the CodeImport table from the ProductSeries table.

This module is the back-end for cronscripts/code-import-sync.py.
"""

__metaclass__ = type
__all__ = ['CodeImportSync']


from zope.component import getUtility

from canonical.lp.dbschema import CodeImportReviewStatus
from canonical.launchpad.interfaces import (
    BranchType, IBranchSet, ICodeImportSet, ILaunchpadCelebrities,
    IProductSeriesSet, ImportStatus, RevisionControlSystems)
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
        self.logger.debug("Committing.")
        self.txn.commit()
        self.logger.debug("Done committing.")
        self.logger.info("Code imports sync complete.")

    def run(self):
        """Synchronize the CodeImport table with the ProductSeries table."""

        # Get all relevant ProductSeries, and all CodeImports.
        self.logger.info("Reading data.")
        self.logger.debug("Reading ProductSeries table.")
        series_map = dict(
            (series.id, series) for series in self.getImportSeries())
        self.logger.debug("Done reading ProductSeries table.")
        self.logger.debug("Reading CodeImport table.")
        code_imports_map = dict(
            (code_import.id, code_import)
            for code_import in getUtility(ICodeImportSet).getAll())
        self.logger.debug("Done reading CodeImport table.")
        series_ids = set(series_map.iterkeys())
        code_import_ids = set(code_imports_map.iterkeys())

        # Create CodeImports for ProductSeries with no matching CodeImport.
        series_id_list = list(sorted(series_ids.difference(code_import_ids)))
        self.logger.info("Creating %d CodeImport rows.", len(series_id_list))
        for series_id in series_id_list:
            series = series_map[series_id]
            self.createCodeImport(series)

        # Update CodeImports from their matching ProductSeries.
        update_id_list = list(sorted(series_ids.intersection(code_import_ids)))
        self.logger.info("Updating %d CodeImport rows.", len(update_id_list))
        for update_id in update_id_list:
            series = series_map[update_id]
            code_import = code_imports_map[update_id]
            self.updateCodeImport(series, code_import)

        # Delete CodeImports not associated to any valid ProductSeries.
        code_import_id_list = list(sorted(
            code_import_ids.difference(series_ids)))
        self.logger.info(
            "Deleting %d CodeImport rows.", len(code_import_id_list))
        for code_import_id in code_import_id_list:
            code_import = code_imports_map[code_import_id]
            self.deleteOrphanedCodeImport(code_import)

    def getImportSeries(self):
        """Iterate over ProductSeries for which we want to have a CodeImport.

        This is any series where importstatus is TESTING, AUTOTESTED,
        PROCESSING, SYNCING or STOPPED.

        Series where importstatus is DONTSYNC or TESTFAILED are ignored.

        Series for non-MAIN CVS branches are also ignored because we do not
        support imports from non-MAIN CVS branches.
        """
        series_iterator = getUtility(IProductSeriesSet).searchImports()
        for series in series_iterator:
            if series.importstatus in (ImportStatus.DONTSYNC,
                                       ImportStatus.TESTFAILED):
                continue
            elif series.importstatus in (ImportStatus.TESTING,
                                         ImportStatus.AUTOTESTED,
                                         ImportStatus.PROCESSING,
                                         ImportStatus.SYNCING,
                                         ImportStatus.STOPPED):
                if series.rcstype == RevisionControlSystems.CVS:
                    if series.cvsbranch != 'MAIN':
                        continue
                yield series
            else:
                assert series.importstatus is not None
                raise AssertionError(
                    "Unknown importstatus: %s", series.importstatus.name)

    def reviewStatusFromImportStatus(self, import_status):
        """Return the `CodeImportReviewStatus` value corresponding to the given
        `ImportStatus` value.
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
            # CodeImport. A non-NULL last_successful means this import was
            # successful, if a later update to this CodeImport sets
            # last_successful to NULL, we must create a new branch. See
            # TestCodeImportSync.testReimportProcess for details
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
        self.logger.debug("Creating CodeImport for series %s/%s (%d).",
            series.product.name, series.name, series.id)
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
                self.logger.debug("Aborted creating CodeImport.")
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
        self.logger.debug("Done creating CodeImport.")
        return code_import

    def updateCodeImport(self, series, code_import):
        """Update `code_import` to match `series`.

        :param series: a ProductSeries associated to a code import.
        :param code_import: The CodeImport corresponding to `series`.
        :postcondition: `code_import` is up to date with `series`.
        """
        self.logger.debug("Updating CodeImport for series %s/%s (%d).",
            series.product.name, series.name, series.id)

        # When code-import-sync runs in production, importd will need to use
        # the CodeImport's branch to publish the import.
        assert (series.import_branch is None
                or code_import.branch == series.import_branch)

        # If the previous date_last_successful was not NULL, and the new one is
        # NULL, that means we are doing a re-import. So we must use a new
        # branch. See TestCodeImportSync.testReimportProcess for details
        date_last_successful = self.dateLastSuccessfulFromProductSeries(series)
        if (code_import.date_last_successful is not None
                and date_last_successful is None):
            self.logger.debug("CodeImport.branch must be reset.")
            new_branch = self.createNewImportBranch(series)
            if new_branch is None:
                # A branch name conflict occured.
                self.logger.debug("Aborted updating CodeImport.")
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
        self.logger.debug("Done updating Codeimport.")

    def createNewImportBranch(self, series):
        """Create a new branch for the CodeImport associated to `series`.

        :param: an import ProductSeries.
        :return: an import branch, or None if a branch name conflict occured.
        """
        self.logger.debug("Creating import branch.")
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        unique_name = '~%s/%s/%s' % (
            vcs_imports.name, series.product.name, series.name)
        branch_set = getUtility(IBranchSet)
        self.logger.debug("Checking name is available: %s", unique_name)
        conflict_branch = branch_set.getByUniqueName(unique_name)
        if conflict_branch is not None:
            # If there is already an import branch by this name, it should
            # probably be renamed or deleted.
            self.logger.error("Branch name conflict: %s",
                canonical_url(conflict_branch))
            return None
        self.logger.debug("Name available, creating branch.")
        branch = getUtility(IBranchSet).new(
            BranchType.IMPORTED,
            name=series.name, creator=vcs_imports, owner=vcs_imports,
            product=series.product, url=None)
        self.logger.debug("Done creating import branch.")
        return branch

    def deleteOrphanedCodeImport(self, code_import):
        """Delete a CodeImport object that is no longer associated to an import
        product series.
        """
        self.logger.debug("Deleting CodeImport %s (%d).",
            code_import.branch.unique_name, code_import.id)
        getUtility(ICodeImportSet).delete(code_import.id)
        self.logger.warning(
            "Branch was orphaned, you may want to delete it: %s",
            canonical_url(code_import.branch))
        self.logger.debug("Done deleting CodeImport.")


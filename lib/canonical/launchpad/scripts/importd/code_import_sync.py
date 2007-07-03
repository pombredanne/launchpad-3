# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Populate and update the CodeImport table from the ProductSeries table.

This module is the back-end for cronscripts/code-import-sync.py.
"""

__metaclass__ = type
__all__ = ['CodeImportSync']


from zope.component import getUtility

from canonical.lp.dbschema import CodeImportReviewStatus, ImportStatus
from canonical.launchpad.interfaces import (
    IBranchSet, ICodeImportSet, ILaunchpadCelebrities, IProductSeriesSet)


class CodeImportSync:
    """Populate and update the CodeImport table from the ProductSeries table.
    """

    def __init__(self, logger, txn):
        self.logger = logger
        self.txn = txn

    def run(self):
        """Entry point method for the script runner."""
        for series in self.getImportSeries():
            code_import = getUtility(ICodeImportSet).get(series.id)
            if code_import is None:
                self.createCodeImport(series)

    def getImportSeries(self):
        """Iterate over ProductSeries for which we want to have a CodeImport.

        This is any series where importstatus is TESTING, AUTOTESTED,
        PROCESSING, SYNCING or STOPPED.

        Series where importstatus is DONTSYNC or TESTFAILED are ignored.
        """
        import_series = getUtility(IProductSeriesSet).search(forimport=True)
        for series in import_series:
            yield series

    def syncOneSeries(self, series):
        """Create or update the CodeImport object associated to the given
        ProductSeries.
        """

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
                % import_status)
        return review_status

    def createCodeImport(self, series):
        """Create the CodeImport object corresponding to the given
        ProductSeries.

        :param series: a ProductSeries associated to a code import.
        :return: the created CodeImport.
        :precondition: The CodeImport object corresponding to `series` does
            already exist in the database.
        :postcondition: The CodeImport object corresponding to `series` exists
            in the database and is up to date.
        """
        date_last_successful = None
        vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
        branch = getUtility(IBranchSet).new(
            series.name, vcs_imports, series.product, None, None)
        code_import = getUtility(ICodeImportSet).newWithId(
            series.id, vcs_imports, branch, series.rcstype,
            svn_branch_url=series.svnrepository,
            cvs_root=series.cvsroot, cvs_module=series.cvsmodule)
        review_status = self.reviewStatusFromImportStatus(series.importstatus)
        code_import.review_status = review_status
        return code_import

    def updateCodeImport(self, series, code_import):
        """Update `code_import` to match `series`.

        :param series: a ProductSeries associated to a code import.
        :param code_import: The CodeImport corresponding to `series`.
        :postcondition: `code_import` is up to date with `series`.
        """

    def getOrphanedCodeImports(self):
        """Find all the CodeImport objects that do not have a corresponding
        ProductSeries.

        :return: iterable of CodeImports.
        """

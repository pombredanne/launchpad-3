# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Populate and update the CodeImport table from the ProductSeries table.

This module is the back-end for cronscripts/code-import-sync.py.
"""

__metaclass__ = type
__all__ = ['CodeImportSync']


class CodeImportSync:
    """Populate and update the CodeImport table from the ProductSeries table.
    """

    def __init__(self, logger, txn):
        self.logger = logger
        self.txn = txn

    def run(self):
        """Entry point method for the script runner."""

    def getImportSeries(self):
        """Select ProductSeries rows for which we want to have a CodeImport.

        This is any series where importstatus is TESTING, AUTOTESTED,
        PROCESSING, SYNCING or STOPPED.

        Series where importstatus is DONTSYNC or TESTFAILED are ignored.
        """
        return []

    def syncOneSeries(self, series):
        """Create or update the CodeImport object associated to the given
        ProductSeries.
        """

    def createCodeImport(self, series):
        """Create the CodeImport object corresponding to the given
        ProductSeries.

        :param series: a ProductSeries associated to a code import.
        :precondition: The CodeImport object corresponding to `series` does
            already exist in the database.
        :postcondition: The CodeImport object corresponding to `series` exists
            in the database and is up to date.
        """

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

# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""View support classes for the bazaar application."""

__metaclass__ = type

__all__ = ['BazaarApplicationView']

from zope.component import getUtility
from canonical.launchpad.interfaces import IProductSeriesSet
from canonical.lp.dbschema import ImportStatus


class BazaarApplicationView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.seriesset = getUtility(IProductSeriesSet)

    def import_count(self):
        return self.seriesset.importcount()

    def testing_count(self):
        return self.seriesset.importcount(ImportStatus.TESTING.value)

    def autotested_count(self):
        return self.seriesset.importcount(ImportStatus.AUTOTESTED.value)

    def testfailed_count(self):
        return self.seriesset.importcount(ImportStatus.TESTFAILED.value)

    def processing_count(self):
        return self.seriesset.importcount(ImportStatus.PROCESSING.value)

    def syncing_count(self):
        return self.seriesset.importcount(ImportStatus.SYNCING.value)

    def stopped_count(self):
        return self.seriesset.importcount(ImportStatus.STOPPED.value)

    def hct_count(self):
        branches = self.seriesset.search(forimport=True,
            importstatus=ImportStatus.SYNCING.value)
        count = 0
        for branch in branches:
            for package in branch.sourcepackages:
                if package.shouldimport:
                    count += 1
                    continue
        return count

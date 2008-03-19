# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test distroseries translations copying."""

__metaclass__ = type


import logging
from unittest import TestCase, TestLoader

from zope.component import getUtility

from canonical.launchpad.ftests import syncUpdate
from canonical.launchpad.interfaces import IDistroSeriesSet
from canonical.launchpad.scripts.copy_distroseries_translations import (
    update_translations)

from canonical.testing import LaunchpadZopelessLayer


class MockTransactionManager:
    def begin(self):
        pass
    def commit(self):
        pass
    def abort(self):
        pass


class MockSeries:
    name = "MockSeries"
    hide_all_translations = False
    defer_translation_imports = False

    def copyMissingTranslationsFromParent(txn, logger):
        raise Exception("Deliberate failure for test purposes.")


class TestCopying(TestCase):
    layer = LaunchpadZopelessLayer
    txn = MockTransactionManager()

    def test_flagsHandling(self):
        """Flags are correctly restored, no matter what their values."""
        series_set = getUtility(IDistroSeriesSet)
        sid = series_set.findByName('sid')[0]

        sid.hide_all_translations = True
        sid.defer_translation_imports = True
        syncUpdate(sid)
        update_translations(sid, self.txn, logging)
        sid = series_set.findByName('sid')[0]
        self.assertTrue(sid.hide_all_translations)
        self.assertTrue(sid.defer_translation_imports)

        sid.hide_all_translations = True
        sid.defer_translation_imports = False
        syncUpdate(sid)
        update_translations(sid, self.txn, logging)
        sid = series_set.findByName('sid')[0]
        self.assertTrue(sid.hide_all_translations)
        self.assertFalse(sid.defer_translation_imports)

        sid.hide_all_translations = False
        sid.defer_translation_imports = True
        syncUpdate(sid)
        update_translations(sid, self.txn, logging)
        sid = series_set.findByName('sid')[0]
        self.assertFalse(sid.hide_all_translations)
        self.assertTrue(sid.defer_translation_imports)

        sid.hide_all_translations = False
        sid.defer_translation_imports = False
        syncUpdate(sid)
        update_translations(sid, self.txn, logging)
        sid = series_set.findByName('sid')[0]
        self.assertFalse(sid.hide_all_translations)
        self.assertFalse(sid.defer_translation_imports)

    def _copyAndFail(self, series):
        """Run copy on a mock DistroSeries which always fails."""
        failed = False
        try:
            update_translations(series, self.txn, logging)
        except Exception:
            failed = True

        self.assertTrue(failed, "Exception while copying was swallowed.")


    def test_errorHandling(self):
        """Test that errors while copying restore flags properly."""
        series = MockSeries()

        series.hide_all_translations = False
        series.defer_translation_imports = False
        self._copyAndFail(series)
        self.assertFalse(series.hide_all_translations)
        self.assertFalse(series.defer_translation_imports)


        series.hide_all_translations = False
        series.defer_translation_imports = True
        self._copyAndFail(series)
        self.assertFalse(series.hide_all_translations)
        self.assertTrue(series.defer_translation_imports)


        series.hide_all_translations = True
        series.defer_translation_imports = False
        self._copyAndFail(series)
        self.assertTrue(series.hide_all_translations)
        self.assertFalse(series.defer_translation_imports)


        series.hide_all_translations = True
        series.defer_translation_imports = True
        self._copyAndFail(series)
        self.assertTrue(series.hide_all_translations)
        self.assertTrue(series.defer_translation_imports)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)


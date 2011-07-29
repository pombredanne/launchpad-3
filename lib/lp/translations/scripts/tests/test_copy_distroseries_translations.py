# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test distroseries translations copying."""

__metaclass__ = type


import logging
from unittest import (
    TestCase,
    )

from zope.component import getUtility

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.registry.interfaces.distroseries import IDistroSeriesSet
from lp.testing.faketransaction import FakeTransaction
from lp.translations.scripts.copy_distroseries_translations import (
    copy_distroseries_translations,
    )


class TestCopying(TestCase):
    layer = LaunchpadZopelessLayer
    txn = FakeTransaction()

    def test_flagsHandling(self):
        """Flags are correctly restored, no matter what their values."""
        series_set = getUtility(IDistroSeriesSet)
        sid = series_set.findByName('sid')[0]

        sid.hide_all_translations = True
        sid.defer_translation_imports = True
        copy_distroseries_translations(sid, self.txn, logging)
        sid = series_set.findByName('sid')[0]
        self.assertTrue(sid.hide_all_translations)
        self.assertTrue(sid.defer_translation_imports)

        sid.hide_all_translations = True
        sid.defer_translation_imports = False
        copy_distroseries_translations(sid, self.txn, logging)
        sid = series_set.findByName('sid')[0]
        self.assertTrue(sid.hide_all_translations)
        self.assertFalse(sid.defer_translation_imports)

        sid.hide_all_translations = False
        sid.defer_translation_imports = True
        copy_distroseries_translations(sid, self.txn, logging)
        sid = series_set.findByName('sid')[0]
        self.assertFalse(sid.hide_all_translations)
        self.assertTrue(sid.defer_translation_imports)

        sid.hide_all_translations = False
        sid.defer_translation_imports = False
        copy_distroseries_translations(sid, self.txn, logging)
        sid = series_set.findByName('sid')[0]
        self.assertFalse(sid.hide_all_translations)
        self.assertFalse(sid.defer_translation_imports)

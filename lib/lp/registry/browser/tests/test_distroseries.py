# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `lp.registry.browser.distroseries`."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    feature_flags,
    set_feature_flag,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class TestDistroSeriesInitializeView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_init(self):
        # There exists a +initseries view for distroseries.
        distroseries = self.factory.makeDistroSeries()
        view = create_initialized_view(distroseries, "+initseries")
        self.assertTrue(view)

    def test_feature_enabled(self):
        # The feature is disabled by default, but can be enabled by setting
        # the soyuz.derived-series-ui.enabled flag.
        distroseries = self.factory.makeDistroSeries()
        view = create_initialized_view(distroseries, "+initseries")
        with feature_flags():
            self.assertFalse(view.is_feature_enabled)
        with feature_flags():
            set_feature_flag(u"soyuz.derived-series-ui.enabled", u"true")
            self.assertTrue(view.is_feature_enabled)

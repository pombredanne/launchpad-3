# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.testing import AppServerLayer
from lp.testing import (
    TestCaseWithFactory,
    ws_object,
    )


class DistroSeriesWebServiceTestCase(TestCaseWithFactory):

    layer = AppServerLayer

    def assertSameDiffs(self, diffs, ws_diffs):
        self.assertEqual(
            sorted([self._wsFor(diff) for diff in diffs]),
            sorted([ws_diff for ws_diff in ws_diffs]))

    def _wsFor(self, obj):
        return ws_object(
            self.factory.makeLaunchpadService(version="beta"), obj)

    def test_getDifferencesTo(self):
        # Distroseries' DistroSeriesDifferences are available
        # on the web service.
        ds_diff = self.factory.makeDistroSeriesDifference()
        ds_diff_ws = self._wsFor(ds_diff.derived_series)

        self.assertSameDiffs([ds_diff], ds_diff_ws.getDifferencesTo())

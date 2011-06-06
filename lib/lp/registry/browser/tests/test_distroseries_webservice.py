# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.testing import AppServerLayer
from lp.registry.enum import (
    DistroSeriesDifferenceStatus,
    DistroSeriesDifferenceType,
    )
from lp.testing import (
    TestCaseWithFactory,
    ws_object,
    )


class DistroSeriesWebServiceTestCase(TestCaseWithFactory):

    layer = AppServerLayer

    def assertSameDiffs(self, diffs, ws_diffs):
        self.assertContentEqual(
            [self._wsFor(diff) for diff in diffs],
            [ws_diff for ws_diff in ws_diffs])

    def _wsFor(self, obj):
        return ws_object(
            self.factory.makeLaunchpadService(version="devel"), obj)

    def test_getDifferencesTo(self):
        # Distroseries' DistroSeriesDifferences are available
        # on the web service.
        # This method is a simple wrapper around getForDistroSeries
        # that is thoroughly tested in test_distroseriesdifference.
        ds_diff = self.factory.makeDistroSeriesDifference()
        ds_ws = self._wsFor(ds_diff.derived_series)

        self.assertSameDiffs([ds_diff], ds_ws.getDifferencesTo(
            status=str(DistroSeriesDifferenceStatus.NEEDS_ATTENTION),
            difference_type=str(
                DistroSeriesDifferenceType.DIFFERENT_VERSIONS),
            source_package_name_filter=ds_diff.source_package_name.name,
            child_version_higher=False,
            parent_series=self._wsFor(ds_diff.parent_series)))

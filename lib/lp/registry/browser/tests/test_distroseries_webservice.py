# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from lazr.restfulclient.errors import BadRequest
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.testing import AppServerLayer
from lp.registry.enum import DistroSeriesDifferenceStatus
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifferenceSource,
    )
from lp.soyuz.enums import PackageDiffStatus
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
        # A distroseries' DistroSeriesDifferences are available
        # on the web service.
        ds_diff = self.factory.makeDistroSeriesDifference()
        ds_diff_ws = self._wsFor(ds_diff.derived_series)
        self.assertSameDiffs([ds_diff], ds_diff_ws.getDifferencesTo())

    def test_getDifferencesTo_types(self):
        pass

    def test_getDifferencesTo_status(self):
        pass

    def test_getDifferencesTo_packagename_filter(self):
        pass

    def test_getDifferencesTo_multiple_parents(self):
        pass

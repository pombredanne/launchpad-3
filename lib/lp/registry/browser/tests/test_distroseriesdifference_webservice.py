# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import with_statement

__metaclass__ = type

from lazr.restfulclient.errors import Unauthorized
from zope.component import getUtility

from canonical.testing import AppServerLayer
from canonical.launchpad.webapp.publisher import canonical_url
from lp.registry.enum import DistroSeriesDifferenceStatus
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifferenceSource,
    )
from lp.testing import (
    launchpadlib_for,
    login_person,
    TestCaseWithFactory,
    ws_object,
    )


class DistroSeriesDifferenceWebServiceTestCase(TestCaseWithFactory):

    layer = AppServerLayer

    def makeLaunchpadService(self, person=None):
        if person is None:
            person = self.factory.makePerson()
        launchpad = launchpadlib_for("test", person,
            service_root="http://api.launchpad.dev:8085")
        login_person(person)
        return launchpad

    def test_get_difference(self):
        # DistroSeriesDifferences are available on the web service.
        ds_diff = self.factory.makeDistroSeriesDifference()
        ds_diff_path = canonical_url(ds_diff).replace(
            'http://launchpad.dev', '')

        ws_diff = ws_object(self.makeLaunchpadService(), ds_diff)

        self.assertTrue(
            ws_diff.self_link.endswith(ds_diff_path))

    def test_blacklist_not_public(self):
        # The blacklist method is not publically available.
        ds_diff = self.factory.makeDistroSeriesDifference()
        ws_diff = ws_object(self.makeLaunchpadService(), ds_diff)

        self.assertRaises(Unauthorized, ws_diff.blacklist)

    def test_blacklist_default(self):
        # By default the specific version will be blacklisted.
        ds_diff = self.factory.makeDistroSeriesDifference()
        ws_diff = ws_object(self.makeLaunchpadService(
            ds_diff.derived_series.owner), ds_diff)

        result = ws_diff.blacklist()

        utility = getUtility(IDistroSeriesDifferenceSource)
        ds_diff = utility.getByDistroSeriesAndName(
            ds_diff.derived_series, ds_diff.source_package_name.name)
        self.assertEqual(
            DistroSeriesDifferenceStatus.BLACKLISTED_CURRENT,
            ds_diff.status)

# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.security.management import endInteraction

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    launchpadlib_for,
    ws_object,
    TestCaseWithFactory,
    )


class TestDistroArchSeriesWebservice(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        distro = self.factory.makeDistribution()
        distroseries = self.factory.makeDistroSeries(
            distribution=distro)
        self.factory.makeDistroArchSeries(
            distroseries=distroseries)

        self.distroseries = distroseries

    def test_distroseries_architectures(self):
        endInteraction()
        launchpad = launchpadlib_for('test', None, version='devel')
        ws_distroseries = ws_object(launchpad, self.distroseries)
        self.assertEqual(1, len(ws_distroseries.architectures))

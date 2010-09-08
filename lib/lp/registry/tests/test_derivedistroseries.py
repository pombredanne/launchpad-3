# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test initialising a distroseries using
IDistroSeries.deriveDistroSeries."""

__metaclass__ = type

from canonical.testing.layers import LaunchpadFunctionalLayer

class TestDeriveDistroSeries(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestDeriveDistroSeries, self).setUp()

    def test_create_new_distroseries(self):
        pass


# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the initialise_distroseries script machinery."""

__metaclass__ = type

from zope.component import getUtility

from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.scripts.initialise_distroseries import (
    InitialiseDistroSeries, ParentSeriesRequired, SeriesAlreadyInUse)
from lp.testing import TestCaseWithFactory

from canonical.launchpad.interfaces import IDistributionSet
from canonical.launchpad.ftests import login, logout
from canonical.testing.layers import LaunchpadZopelessLayer


class TestInitialiseDistroSeries(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestInitialiseDistroSeries, self).setUp()
        login("foo.bar@canonical.com")
        distribution_set = getUtility(IDistributionSet)
        self.ubuntutest = distribution_set['ubuntutest']
        ubuntu = distribution_set['ubuntu']
        self.hoary = ubuntu['hoary']
        # XXX cprov 2006-05-29 bug=49133:
        # New distroseries should be provided by IDistribution.
        # This maybe affected by derivation design and is documented in bug.
        self.foobuntu = self.ubuntutest.newSeries(
            'foobuntu', 'FooBuntu', 'The Foobuntu', 'yeck', 'doom',
            '888', None, self.hoary.owner)
        logout()

    def test_failure_with_no_parent_series(self):
        self.assertRaises(
            ParentSeriesRequired, InitialiseDistroSeries, self.foobuntu)

    def test_failure_for_already_released_distroseries(self):
        login("foo.bar@canonical.com")
        breezy_autotest = self.ubuntutest['breezy-autotest']
        self.assertRaises(
            SeriesAlreadyInUse, InitialiseDistroSeries, breezy_autotest)
        logout()

    def test_failure_with_pending_builds(self):
        pass

    def test_failure_with_queue_items(self):
        pass

    def test_initialise(self):
        pass


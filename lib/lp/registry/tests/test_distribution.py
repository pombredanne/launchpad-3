# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for Distribution."""

__metaclass__ = type

import unittest

from lp.registry.tests.test_distroseries import (
    TestDistroSeriesCurrentSourceReleases)
from canonical.launchpad.interfaces.distributionsourcepackagerelease import (
    IDistributionSourcePackageRelease)
from lp.registry.interfaces.distroseries import DistroSeriesStatus


class TestDistributionCurrentSourceReleases(
    TestDistroSeriesCurrentSourceReleases):
    """Test for Distribution.getCurrentSourceReleases().

    This works in the same way as
    DistroSeries.getCurrentSourceReleases() works, except that we look
    for the latest published source across multiple distro series.
    """

    release_interface = IDistributionSourcePackageRelease

    @property
    def test_target(self):
        return self.distribution

    def test_which_distroseries_does_not_matter(self):
        # When checking for the current release, we only care about the
        # version numbers. We don't care whether the version is
        # published in a earlier or later series.
        self.current_series = self.factory.makeDistroRelease(
            self.distribution, '1.0', status=DistroSeriesStatus.CURRENT)
        self.publisher.getPubSource(
            version='0.9', distroseries=self.current_series)
        self.publisher.getPubSource(
            version='1.0', distroseries=self.development_series)
        self.assertCurrentVersion('1.0')

        self.publisher.getPubSource(
            version='1.1', distroseries=self.current_series)
        self.assertCurrentVersion('1.1')


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestDistributionCurrentSourceReleases))
    return suite


# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Model tests for the DistroSeriesDifference class."""

__metaclass__ = type

import unittest

from storm.store import Store

from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifference,
    )
from lp.registry.model.distroseriesdifference import DistroSeriesDifference


class DistroSeriesDifferenceTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_implements_interface(self):
        parent_series = self.factory.makeDistroSeries()
        distro_series = self.factory.makeDistroSeries(
            parent_series=parent_series)
        spph = self.factory.makeSourcePackagePublishingHistory(
            distroseries=distro_series)
        parent_spph = self.factory.makeSourcePackagePublishingHistory(
            distroseries=parent_series,
            sourcepackagename=spph.sourcepackagerelease.sourcepackagename)
        diff = DistroSeriesDifference()
        diff.distro_series = distro_series
        diff.source_package = spph
        diff.parent_source_package = parent_spph
        store = Store.of(distro_series)
        store.add(diff)

        diff_reloaded = store.find(
            DistroSeriesDifference, DistroSeriesDifference.id == diff.id)

        verifyObject(IDistroSeriesDifference, diff_reloaded)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

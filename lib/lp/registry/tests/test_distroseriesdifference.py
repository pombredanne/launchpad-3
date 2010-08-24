# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Model tests for the DistroSeriesDifference class."""

__metaclass__ = type

import unittest

from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory
from lp.registry.exceptions import NotADerivedSeriesError
from lp.registry.interfaces.distroseriesdifference import (
    IDistroSeriesDifference,
    )


class DistroSeriesDifferenceTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_implements_interface(self):
        # The implementation implements the interface correctly.
        ds_diff = self.factory.makeDistroSeriesDifference()

        verifyObject(IDistroSeriesDifference, ds_diff)

    def test_at_least_one_source_package(self):
        self.fail('Not implemented. Waiting on implementation feedback.')

    def test_new_non_derived_series(self):
        # A DistroSeriesDifference cannot be created with a non-derived
        # series.
        distro_series = self.factory.makeDistroSeries()
        self.assertRaises(
            NotADerivedSeriesError,
            self.factory.makeDistroSeriesDifference,
            derived_series=distro_series)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for ISuiteSourcePackage."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.model.suitesourcepackage import SuiteSourcePackage
from lp.testing import TestCaseWithFactory


class TestSuiteSourcePackage(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_construction(self):
        # A SuiteSourcePackage is constructed from an `IDistroSeries`, a
        # `PackagePublishingPocket` enum and an `ISourcePackageName`. These
        # are all provided as attributes.
        distroseries = self.factory.makeDistroSeries()
        pocket = PackagePublishingPocket.RELEASE
        sourcepackagename = self.factory.makeSourcePackageName()
        ssp = SuiteSourcePackage(distroseries, pocket, sourcepackagename)
        self.assertEqual(distroseries, ssp.distroseries)
        self.assertEqual(pocket, ssp.pocket)
        self.assertEqual(sourcepackagename, ssp.sourcepackagename)

    def test_sourcepackage(self):
        # A SuiteSourcePackage has a `sourcepackage` property, which is an
        # ISourcePackage that represents the sourcepackagename, distroseries
        # pair.
        ssp = self.factory.makeSuiteSourcePackage()
        package = ssp.distroseries.getSourcePackage(ssp.sourcepackagename)
        self.assertEqual(package, ssp.sourcepackage)

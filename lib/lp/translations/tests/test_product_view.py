# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest

from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import LaunchpadZopelessLayer
from lp.registry.browser.product import ProductView
from lp.testing import TestCaseWithFactory


class TestProduct(TestCaseWithFactory):
    """Test Product view in translations facet."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        # Create a product that uses translations.
        TestCaseWithFactory.setUp(self)
        self.product = self.factory.makeProduct()
        self.series = self.product.development_focus
        self.product.official_rosetta = True
        self.view = ProductView(self.product,
                                LaunchpadTestRequest())

    def test_primary_translatable_with_package_link(self):
        # If development focus series is linked to
        # a distribution package with translations,
        # we do not try to show translation statistics
        # for the package.
        sourcepackage = self.factory.makeSourcePackage()
        sourcepackage.setPackaging(self.series, None)
        sourcepackage.distroseries.distribution.official_rosetta = True
        pot = self.factory.makePOTemplate(
            distroseries=sourcepackage.distroseries,
            sourcepackagename=sourcepackage.sourcepackagename)
        self.assertEquals(self.view.primary_translatable, {})

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

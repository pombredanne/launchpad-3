# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type
import unittest

from canonical.doap.fileimporter import ProductReleaseImporter
from canonical.launchpad.database import Product
from canonical.testing import LaunchpadFunctionalLayer

class ProductReleaseImporterTestCase(unittest.TestCase):
    layer = LaunchpadFunctionalLayer

    def test_ensureProductRelease(self):
        importer = ProductReleaseImporter(Product.byName('firefox'))

        # This should create a release
        pr = importer._ensureProductRelease('firefox-999.99.tar.gz')

        # This should fetch the already created one
        pr2 = importer._ensureProductRelease('firefox-999.99.tar.gz')
        self.assertEqual(pr.id, pr2.id)

        # Check the version is right
        self.assertEqual('999.99', pr.version)


def test_suite():
    return unittest.makeSuite(ProductReleaseImporterTestCase)

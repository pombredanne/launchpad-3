# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Unit tests for ISourcePackage implementations."""

__metaclass__ = type

import unittest

from canonical.launchpad.testing import TestCaseWithFactory
from canonical.testing.layers import DatabaseFunctionalLayer


class TestSourcePackage(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_path(self):
        sourcepackage = self.factory.makeSourcePackage()
        self.assertEqual(
            '%s/%s/%s' % (
                sourcepackage.distribution.name,
                sourcepackage.distroseries.name,
                sourcepackage.sourcepackagename.name),
            sourcepackage.path)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


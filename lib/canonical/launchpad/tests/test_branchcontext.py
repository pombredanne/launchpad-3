# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for branch contexts."""

__metaclass__ = type

import unittest

from canonical.launchpad.database.branchcontext import (
    JunkContext, PackageContext)
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.testing import DatabaseFunctionalLayer


class TestJunkContext(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_name(self):
        # The name of a junk context is '+junk'.
        context = JunkContext()
        self.assertEqual('+junk', context.name)


class TestPackageContext(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_name(self):
        # The name of a package context is distro/series/sourcepackage
        distroseries = self.factory.makeDistroRelease()
        sourcepackagename = self.factory.makeSourcePackageName()
        context = PackageContext(distroseries, sourcepackagename)
        self.assertEqual(
            '%s/%s/%s' % (
                distroseries.distribution.name,
                distroseries.name,
                sourcepackagename.name), context.name)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


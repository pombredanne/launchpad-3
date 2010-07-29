# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test SourcePackageRelease."""

__metaclass__ = type

from canonical.testing import LaunchpadFunctionalLayer

from lp.testing import TestCaseWithFactory


class TestSourcePackageRelease(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_uploader_package(self):
        spr = self.factory.makeSourcePackageRelease()
        self.assertEqual(spr.uploader, None)


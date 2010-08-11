# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test BinaryPackageRelease."""

__metaclass__ = type

from canonical.testing import LaunchpadFunctionalLayer

from lp.soyuz.interfaces.binarypackagerelease import (
    IBinaryPackageRelease, BinaryPackageFormat)
from lp.soyuz.interfaces.publishing import (
    PackagePublishingPriority,)

from lp.testing import TestCaseWithFactory


class TestBinaryPackageRelease(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_provides(self):
        build = self.factory.makeBinaryPackageBuild()
        release = build.createBinaryPackageRelease(
                binarypackagename=self.factory.makeBinaryPackageName(),
                version="0.1", summary="My package",
                description="My description",
                binpackageformat=BinaryPackageFormat.DEB,
                component=self.factory.makeComponent("main"),
                section=self.factory.makeSection("net"),
                priority=PackagePublishingPriority.OPTIONAL,
                installedsize=0, architecturespecific=False)
        self.assertProvides(release, IBinaryPackageRelease)

    def test_user_defined_fields(self):
        build = self.factory.makeBinaryPackageBuild()
        release = build.createBinaryPackageRelease(
                binarypackagename=self.factory.makeBinaryPackageName(),
                version="0.1", summary="My package",
                description="My description",
                binpackageformat=BinaryPackageFormat.DEB,
                component=self.factory.makeComponent("main"),
                section=self.factory.makeSection("net"),
                priority=PackagePublishingPriority.OPTIONAL,
                installedsize=0, architecturespecific=False,
                user_defined_fields=[
                    ("Python-Version", ">= 2.4"),
                    ("Other", "Bla")])
        self.assertEquals([
            ["Python-Version", ">= 2.4"],
            ["Other", "Bla"]], release.user_defined_fields)

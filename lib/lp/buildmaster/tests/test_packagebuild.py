# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `IPackageBuild`."""

__metaclass__ = type

import unittest

from storm.store import Store
from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer

from lp.buildmaster.interfaces.packagebuild import (
    IPackageBuild, IPackageBuildSource)
from lp.buildmaster.model.packagebuild import PackageBuild
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.testing import TestCaseWithFactory


class TestPackageBuild(TestCaseWithFactory):
    """Tests for the package build object."""

    layer = DatabaseFunctionalLayer

    def makePackageBuild(self):
        return getUtility(IPackageBuildSource).new(
            archive=self.factory.makeArchive(),
            pocket=PackagePublishingPocket.RELEASE)

    def test_providesInterface(self):
        # PackageBuild provides IPackageBuild
        package_build = self.makePackageBuild()
        self.assertProvides(package_build, IPackageBuild)

    def test_saves_record(self):
        # A package build can be stored in the database.
        package_build = self.makePackageBuild()
        store = Store.of(package_build)
        retrieved_build = store.find(
            PackageBuild,
            PackageBuild.id == package_build.id)
        self.assertEqual(package_build, retrieved_build)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

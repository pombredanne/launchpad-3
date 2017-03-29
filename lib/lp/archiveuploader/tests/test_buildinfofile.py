# Copyright 2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Build information file tests."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from debian.deb822 import Changes

from lp.archiveuploader.buildinfofile import BuildInfoFile
from lp.archiveuploader.nascentuploadfile import UploadError
from lp.archiveuploader.tests.test_nascentuploadfile import (
    PackageUploadFileTestCase,
    )
from lp.testing.layers import LaunchpadZopelessLayer


class TestBuildInfoFile(PackageUploadFileTestCase):

    layer = LaunchpadZopelessLayer

    def getBaseBuildInfo(self):
        # XXX cjwatson 2017-03-20: This will need to be fleshed out if we
        # ever start doing non-trivial buildinfo parsing.
        # A Changes object is close enough.
        buildinfo = Changes()
        buildinfo["Format"] = "0.1"
        return buildinfo

    def makeBuildInfoFile(self, filename, buildinfo, component_and_section,
                          priority_name, package, version, changes):
        path, md5, sha1, size = self.writeUploadFile(
            filename, buildinfo.dump())
        return BuildInfoFile(
            path, {"MD5": md5}, size, component_and_section, priority_name,
            package, version, changes, self.policy, self.logger)

    def test_properties(self):
        buildinfo = self.getBaseBuildInfo()
        changes = self.getBaseChanges()
        for (arch, is_sourceful, is_binaryful, is_archindep) in (
                ("source", True, False, False),
                ("all", False, True, True),
                ("i386", False, True, False),
                ):
            buildinfofile = self.makeBuildInfoFile(
                "foo_0.1-1_%s.buildinfo" % arch, buildinfo,
                "main/net", "extra", "dulwich", "0.42",
                self.createChangesFile("foo_0.1-1_%s.changes" % arch, changes))
            self.assertEqual(arch, buildinfofile.architecture)
            self.assertEqual(is_sourceful, buildinfofile.is_sourceful)
            self.assertEqual(is_binaryful, buildinfofile.is_binaryful)
            self.assertEqual(is_archindep, buildinfofile.is_archindep)

    def test_storeInDatabase(self):
        buildinfo = self.getBaseBuildInfo()
        changes = self.getBaseChanges()
        buildinfofile = self.makeBuildInfoFile(
            "foo_0.1-1_source.buildinfo", buildinfo,
            "main/net", "extra", "dulwich", "0.42",
            self.createChangesFile("foo_0.1-1_source.changes", changes))
        lfa = buildinfofile.storeInDatabase()
        self.layer.txn.commit()
        self.assertEqual(buildinfo.dump(), lfa.read())

    def test_checkBuild(self):
        das = self.factory.makeDistroArchSeries(
            distroseries=self.policy.distroseries, architecturetag="i386")
        build = self.factory.makeBinaryPackageBuild(
            distroarchseries=das, archive=self.policy.archive)
        buildinfo = self.getBaseBuildInfo()
        changes = self.getBaseChanges()
        buildinfofile = self.makeBuildInfoFile(
            "foo_0.1-1_i386.buildinfo", buildinfo,
            "main/net", "extra", "dulwich", "0.42",
            self.createChangesFile("foo_0.1-1_i386.changes", changes))
        buildinfofile.checkBuild(build)

    def test_checkBuild_inconsistent(self):
        das = self.factory.makeDistroArchSeries(
            distroseries=self.policy.distroseries, architecturetag="amd64")
        build = self.factory.makeBinaryPackageBuild(
            distroarchseries=das, archive=self.policy.archive)
        buildinfo = self.getBaseBuildInfo()
        changes = self.getBaseChanges()
        buildinfofile = self.makeBuildInfoFile(
            "foo_0.1-1_i386.buildinfo", buildinfo,
            "main/net", "extra", "dulwich", "0.42",
            self.createChangesFile("foo_0.1-1_i386.changes", changes))
        self.assertRaises(UploadError, buildinfofile.checkBuild, build)

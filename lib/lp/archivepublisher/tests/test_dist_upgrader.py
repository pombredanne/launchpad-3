# Copyright 2012-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test dist-upgrader custom uploads.

See also lp.soyuz.tests.test_distroseriesqueue_dist_upgrader for high-level
tests of dist-upgrader upload and queue manipulation.
"""

import os
from textwrap import dedent

from testtools.matchers import DirContains
from zope.component import getUtility

from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.customupload import (
    CustomUploadAlreadyExists,
    CustomUploadBadUmask,
    )
from lp.archivepublisher.dist_upgrader import (
    DistUpgraderBadVersion,
    DistUpgraderUpload,
    )
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.services.tarfile_helpers import LaunchpadWriteTarFile
from lp.soyuz.enums import ArchivePurpose
from lp.testing import TestCaseWithFactory
from lp.testing.layers import ZopelessDatabaseLayer


class FakeConfig:
    """A fake publisher configuration."""
    def __init__(self, archiveroot):
        self.archiveroot = archiveroot


class TestDistUpgrader(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestDistUpgrader, self).setUp()
        self.temp_dir = self.makeTemporaryDirectory()
        self.distro = self.factory.makeDistribution()
        db_pubconf = getUtility(IPublisherConfigSet).getByDistribution(
            self.distro)
        db_pubconf.root_dir = unicode(self.temp_dir)
        self.archive = self.factory.makeArchive(
            distribution=self.distro, purpose=ArchivePurpose.PRIMARY)
        self.suite = "distroseries"
        # CustomUpload.installFiles requires a umask of 0o022.
        old_umask = os.umask(0o022)
        self.addCleanup(os.umask, old_umask)

    def openArchive(self, version):
        self.path = os.path.join(
            self.temp_dir, "dist-upgrader_%s_all.tar.gz" % version)
        self.buffer = open(self.path, "wb")
        self.tarfile = LaunchpadWriteTarFile(self.buffer)

    def process(self):
        self.tarfile.close()
        self.buffer.close()
        DistUpgraderUpload().process(self.archive, self.path, self.suite)

    def getUpgraderPath(self):
        pubconf = getPubConfig(self.archive)
        return os.path.join(
            pubconf.archiveroot, "dists", self.suite, "main",
            "dist-upgrader-all")

    def test_basic(self):
        # Processing a simple correct tar file works.
        self.openArchive("20060302.0120")
        self.tarfile.add_file("20060302.0120/hello", "world")
        self.process()

    def test_already_exists(self):
        # If the target directory already exists, processing fails.
        self.openArchive("20060302.0120")
        self.tarfile.add_file("20060302.0120/hello", "world")
        os.makedirs(os.path.join(self.getUpgraderPath(), "20060302.0120"))
        self.assertRaises(CustomUploadAlreadyExists, self.process)

    def test_bad_umask(self):
        # The umask must be 0o022 to avoid incorrect permissions.
        self.openArchive("20060302.0120")
        self.tarfile.add_file("20060302.0120/file", "foo")
        os.umask(0o002)  # cleanup already handled by setUp
        self.assertRaises(CustomUploadBadUmask, self.process)

    def test_current_symlink(self):
        # A "current" symlink is created to the last version.
        self.openArchive("20060302.0120")
        self.tarfile.add_file("20060302.0120/hello", "world")
        self.process()
        upgrader_path = self.getUpgraderPath()
        self.assertContentEqual(
            ["20060302.0120", "current"], os.listdir(upgrader_path))
        self.assertEqual(
            "20060302.0120",
            os.readlink(os.path.join(upgrader_path, "current")))
        self.assertContentEqual(
            ["hello"],
            os.listdir(os.path.join(upgrader_path, "20060302.0120")))

    def test_bad_version(self):
        # Bad versions in the tarball are refused.
        self.openArchive("20070219.1234")
        self.tarfile.add_file("foobar/foobar/dapper.tar.gz", "")
        self.assertRaises(DistUpgraderBadVersion, self.process)

    def test_sign_with_external_run_parts(self):
        parts_directory = self.makeTemporaryDirectory()
        sign_directory = os.path.join(
            parts_directory, self.distro.name, "sign.d")
        os.makedirs(sign_directory)
        with open(os.path.join(sign_directory, "10-sign"), "w") as f:
            f.write(dedent("""\
                #! /bin/sh
                touch "$OUTPUT_PATH"
                """))
            os.fchmod(f.fileno(), 0o755)
        self.pushConfig("archivepublisher", run_parts_location=parts_directory)
        self.openArchive("20060302.0120")
        self.tarfile.add_file("20060302.0120/list", "a list")
        self.tarfile.add_file("20060302.0120/foo.tar.gz", "a tarball")
        self.process()
        self.assertThat(
            os.path.join(self.getUpgraderPath(), "20060302.0120"),
            DirContains(["list", "foo.tar.gz", "foo.tar.gz.gpg"]))

    def test_getSeriesKey_extracts_architecture(self):
        # getSeriesKey extracts the architecture from an upload's filename.
        self.openArchive("20060302.0120")
        self.assertEqual("all", DistUpgraderUpload.getSeriesKey(self.path))

    def test_getSeriesKey_returns_None_on_mismatch(self):
        # getSeriesKey returns None if the filename does not match the
        # expected pattern.
        self.assertIsNone(DistUpgraderUpload.getSeriesKey("argh_1.0.jpg"))

    def test_getSeriesKey_refuses_names_with_wrong_number_of_fields(self):
        # getSeriesKey requires exactly three fields.
        self.assertIsNone(DistUpgraderUpload.getSeriesKey(
            "package_1.0.tar.gz"))
        self.assertIsNone(DistUpgraderUpload.getSeriesKey(
            "one_two_three_four_5.tar.gz"))

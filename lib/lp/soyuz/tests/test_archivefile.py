# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""ArchiveFile tests."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
import os

import pytz
from testtools.matchers import LessThan
import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.services.database.sqlbase import flush_database_caches
from lp.services.osutils import open_for_writing
from lp.soyuz.interfaces.archivefile import IArchiveFileSet
from lp.testing import TestCaseWithFactory
from lp.testing.layers import LaunchpadZopelessLayer


class TestArchiveFile(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_new(self):
        archive = self.factory.makeArchive()
        library_file = self.factory.makeLibraryFileAlias()
        archive_file = getUtility(IArchiveFileSet).new(
            archive, "foo", "dists/foo", library_file)
        self.assertEqual(archive, archive_file.archive)
        self.assertEqual("foo", archive_file.container)
        self.assertEqual("dists/foo", archive_file.path)
        self.assertEqual(library_file, archive_file.library_file)
        self.assertIsNone(archive_file.scheduled_deletion_date)

    def test_newFromFile(self):
        root = self.makeTemporaryDirectory()
        with open_for_writing(os.path.join(root, "dists/foo"), "w") as f:
            f.write("abc\n")
        archive = self.factory.makeArchive()
        with open(os.path.join(root, "dists/foo"), "rb") as f:
            archive_file = getUtility(IArchiveFileSet).newFromFile(
                archive, "foo", "dists/foo", f, 4, "text/plain")
        transaction.commit()
        self.assertEqual(archive, archive_file.archive)
        self.assertEqual("foo", archive_file.container)
        self.assertEqual("dists/foo", archive_file.path)
        archive_file.library_file.open()
        try:
            self.assertEqual("abc\n", archive_file.library_file.read())
        finally:
            archive_file.library_file.close()
        self.assertIsNone(archive_file.scheduled_deletion_date)

    def test_getByArchive(self):
        archives = [self.factory.makeArchive(), self.factory.makeArchive()]
        archive_files = []
        for archive in archives:
            archive_files.append(self.factory.makeArchiveFile(archive=archive))
            archive_files.append(self.factory.makeArchiveFile(
                archive=archive, container="foo"))
        archive_file_set = getUtility(IArchiveFileSet)
        self.assertContentEqual(
            archive_files[:2], archive_file_set.getByArchive(archives[0]))
        self.assertContentEqual(
            [archive_files[1]],
            archive_file_set.getByArchive(archives[0], container="foo"))
        self.assertContentEqual(
            [], archive_file_set.getByArchive(archives[0], container="bar"))
        self.assertContentEqual(
            [archive_files[1]],
            archive_file_set.getByArchive(
                archives[0], path=archive_files[1].path))
        self.assertContentEqual(
            [], archive_file_set.getByArchive(archives[0], path="other"))
        self.assertContentEqual(
            archive_files[2:], archive_file_set.getByArchive(archives[1]))
        self.assertContentEqual(
            [archive_files[3]],
            archive_file_set.getByArchive(archives[1], container="foo"))
        self.assertContentEqual(
            [], archive_file_set.getByArchive(archives[1], container="bar"))
        self.assertContentEqual(
            [archive_files[3]],
            archive_file_set.getByArchive(
                archives[1], path=archive_files[3].path))
        self.assertContentEqual(
            [], archive_file_set.getByArchive(archives[1], path="other"))

    def test_scheduleDeletion(self):
        archive_files = [self.factory.makeArchiveFile() for _ in range(3)]
        expected_rows = [
            (archive_file.container, archive_file.path,
             archive_file.library_file.content.sha256)
            for archive_file in archive_files[:2]]
        rows = getUtility(IArchiveFileSet).scheduleDeletion(
            archive_files[:2], timedelta(days=1))
        self.assertContentEqual(expected_rows, rows)
        flush_database_caches()
        tomorrow = datetime.now(pytz.UTC) + timedelta(days=1)
        # Allow a bit of timing slack for slow tests.
        self.assertThat(
            tomorrow - archive_files[0].scheduled_deletion_date,
            LessThan(timedelta(minutes=5)))
        self.assertThat(
            tomorrow - archive_files[1].scheduled_deletion_date,
            LessThan(timedelta(minutes=5)))
        self.assertIsNone(archive_files[2].scheduled_deletion_date)

    def test_unscheduleDeletion(self):
        archives = [self.factory.makeArchive() for _ in range(2)]
        lfas = [
            self.factory.makeLibraryFileAlias(db_only=True) for _ in range(3)]
        archive_files = []
        for archive in archives:
            for container in ("foo", "bar"):
                archive_files.extend([
                    self.factory.makeArchiveFile(
                        archive=archive, container=container, library_file=lfa)
                    for lfa in lfas])
        now = datetime.now(pytz.UTC)
        for archive_file in archive_files:
            removeSecurityProxy(archive_file).scheduled_deletion_date = now
        expected_rows = [
            ("foo", archive_files[0].path, lfas[0].content.sha256),
            ("foo", archive_files[1].path, lfas[1].content.sha256),
            ]
        rows = getUtility(IArchiveFileSet).unscheduleDeletion(
            archive=archives[0], container="foo",
            sha256_checksums=[lfas[0].content.sha256, lfas[1].content.sha256])
        self.assertContentEqual(expected_rows, rows)
        flush_database_caches()
        self.assertContentEqual(
            [archive_files[0], archive_files[1]],
            [archive_file for archive_file in archive_files
             if archive_file.scheduled_deletion_date is None])

    def test_getContainersToReap(self):
        archive = self.factory.makeArchive()
        archive_files = []
        for container in ("release:foo", "other:bar", "baz"):
            for _ in range(2):
                archive_files.append(self.factory.makeArchiveFile(
                    archive=archive, container=container))
        other_archive = self.factory.makeArchive()
        archive_files.append(self.factory.makeArchiveFile(
            archive=other_archive, container="baz"))
        now = datetime.now(pytz.UTC)
        removeSecurityProxy(archive_files[0]).scheduled_deletion_date = (
            now - timedelta(days=1))
        removeSecurityProxy(archive_files[1]).scheduled_deletion_date = (
            now - timedelta(days=1))
        removeSecurityProxy(archive_files[2]).scheduled_deletion_date = (
            now + timedelta(days=1))
        removeSecurityProxy(archive_files[6]).scheduled_deletion_date = (
            now - timedelta(days=1))
        archive_file_set = getUtility(IArchiveFileSet)
        self.assertContentEqual(
            ["release:foo"], archive_file_set.getContainersToReap(archive))
        self.assertContentEqual(
            ["baz"], archive_file_set.getContainersToReap(other_archive))
        removeSecurityProxy(archive_files[3]).scheduled_deletion_date = (
            now - timedelta(days=1))
        self.assertContentEqual(
            ["release:foo", "other:bar"],
            archive_file_set.getContainersToReap(archive))
        self.assertContentEqual(
            ["release:foo"],
            archive_file_set.getContainersToReap(
                archive, container_prefix="release:"))

    def test_reap(self):
        archive = self.factory.makeArchive()
        archive_files = [
            self.factory.makeArchiveFile(archive=archive, container="foo")
            for _ in range(3)]
        archive_files.append(self.factory.makeArchiveFile(archive=archive))
        other_archive = self.factory.makeArchive()
        archive_files.append(
            self.factory.makeArchiveFile(archive=other_archive))
        now = datetime.now(pytz.UTC)
        removeSecurityProxy(archive_files[0]).scheduled_deletion_date = (
            now - timedelta(days=1))
        removeSecurityProxy(archive_files[1]).scheduled_deletion_date = (
            now + timedelta(days=1))
        removeSecurityProxy(archive_files[3]).scheduled_deletion_date = (
            now - timedelta(days=1))
        removeSecurityProxy(archive_files[4]).scheduled_deletion_date = (
            now - timedelta(days=1))
        archive_file_set = getUtility(IArchiveFileSet)
        expected_rows = [
            ("foo", archive_files[0].path,
             archive_files[0].library_file.content.sha256),
            ]
        rows = archive_file_set.reap(archive, container="foo")
        self.assertContentEqual(expected_rows, rows)
        self.assertContentEqual(
            archive_files[1:4], archive_file_set.getByArchive(archive))

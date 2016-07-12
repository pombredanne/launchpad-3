# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test meta-data custom uploads."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

import os

from testtools.matchers import (
    FileContains,
    Not,
    PathExists,
    )
import transaction
from zope.component import getUtility

from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.meta_data import MetaDataUpload
from lp.registry.interfaces.distribution import IDistributionSet
from lp.services.log.logger import BufferLogger
from lp.testing import TestCaseWithFactory
from lp.testing.layers import LaunchpadZopelessLayer


class TestMetaData(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_ubuntu_ppa(self):
        """A meta-data upload to an Ubuntu PPA is published.

        The custom file is published to
        /<person_name>/meta/<ppa_name>/<filename>.
        """
        ubuntu = getUtility(IDistributionSet)["ubuntu"]
        archive = self.factory.makeArchive(distribution=ubuntu)
        packageupload = self.factory.makePackageUpload(archive=archive)
        content = self.factory.getUniqueString()
        libraryfilealias = self.factory.makeLibraryFileAlias(content=content)
        transaction.commit()
        logger = BufferLogger()
        MetaDataUpload(logger=logger).process(packageupload, libraryfilealias)
        self.assertEqual("", logger.getLogBuffer())
        published_file = os.path.join(
            getPubConfig(archive).distroroot, archive.owner.name, "meta",
            archive.name, libraryfilealias.filename)
        self.assertThat(published_file, FileContains(content))

    def test_non_ubuntu_ppa(self):
        """A meta-data upload to a non-Ubuntu PPA is not published.

        The meta-data directory is currently only defined for Ubuntu PPAs.
        """
        archive = self.factory.makeArchive(
            distribution=self.factory.makeDistribution())
        packageupload = self.factory.makePackageUpload(archive=archive)
        libraryfilealias = self.factory.makeLibraryFileAlias(db_only=True)
        logger = BufferLogger()
        MetaDataUpload(logger=logger).process(packageupload, libraryfilealias)
        self.assertEqual(
            "DEBUG Skipping meta-data for archive without metaroot.\n",
            logger.getLogBuffer())
        published_file = os.path.join(
            getPubConfig(archive).distroroot, archive.owner.name, "meta",
            archive.name, libraryfilealias.filename)
        self.assertThat(published_file, Not(PathExists()))

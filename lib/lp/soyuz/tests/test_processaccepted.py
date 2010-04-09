# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test process-accepted.py"""

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.scripts import QuietFakeLogger
from canonical.testing import LaunchpadZopelessLayer

from lp.registry.interfaces.distribution import IDistributionSet
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.scripts.processaccepted import ProcessAccepted
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


class TestProcessAccepted(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer
    dbuser = config.uploadqueue.dbuser

    def setUp(self):
        """Create the Soyuz test publisher."""
        TestCaseWithFactory.setUp(self)
        self.stp = SoyuzTestPublisher()
        self.stp.prepareBreezyAutotest()
        self.test_package_name = "accept-test"

    def getScript(self, test_args=None):
        """Return a ProcessAccepted instance."""
        if test_args is None:
            test_args = []
        test_args.append(self.stp.ubuntutest.name)
        script = ProcessAccepted("process accepted", test_args=test_args)
        script.logger = QuietFakeLogger()
        script.txn = self.layer.txn
        return script

    def createWaitingAcceptancePackage(self, archive=None):
        """Create some pending publications."""
        if archive is None:
            archive = getUtility(
                IDistributionSet).getByName('ubuntu').main_archive
        return self.stp.getPubSource(
            archive=archive, sourcename=self.test_package_name, spr_only=True)

    def testAcceptCopyArchives(self):
        """Test that publications in a copy archive are accepted properly."""
        # Upload some pending packages in a copy archive.
        copy_archive = self.factory.makeArchive(
            distribution=self.stp.ubuntutest, purpose=ArchivePurpose.COPY)
        copy_source = self.createWaitingAcceptancePackage(
            archive=copy_archive)
        # Also upload some stuff in the main archive.
        main_source = self.createWaitingAcceptancePackage()

        # Before accepting, the package should not be published at all.
        published_copy = copy_archive.getPublishedSources(
            name=self.test_package_name)
        # Using .count() until Storm fixes __nonzero__ on SQLObj result
        # sets, then we can use bool() which is far more efficient than
        # counting.
        self.assertEqual(published_copy.count(), 0)

        # Accept the packages.
        script = self.getScript(['--copy-archives'])
        self.layer.txn.commit()
        self.layer.switchDbUser(self.dbuser)
        script.main()

        # Packages in main archive should not be accepted and published.
        published_main = self.stp.ubuntutest.main_archive.getPublishedSources(
            name=self.test_package_name)
        self.assertEqual(published_main.count(), 0)

        # Check the copy archive source was accepted.
        [published_copy] = copy_archive.getPublishedSources(
            name=self.test_package_name)
        self.assertEqual(
            published_copy.status, PackagePublishingStatus.PENDING)
        self.assertEqual(copy_source, published_copy.sourcepackagerelease)


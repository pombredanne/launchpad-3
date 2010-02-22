# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test process-accepted.py"""

from storm.store import Store

from canonical.config import config
from canonical.launchpad.scripts import QuietFakeLogger
from canonical.testing import LaunchpadZopelessLayer

from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.scripts.processaccepted import ProcessAccepted
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


class TestProcessAccepted(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer
    dbuser = config.uploadqueue.dbuser

    def setUp(self):
        """Create the Soyuz test publisher."""
        self.stp = SoyuzTestPublisher()
        self.stp.prepareBreezyAutotest()

    def getScript(self, test_args=None):
        """Return a ProcessAccepted instance."""
        if test_args is None:
            test_args = []
        script = ProcessAccepted("process accepted", test_args=test_args)
        script.logger = QuietFakeLogger()
        script.txn = self.layer.txn
        return script

    def createPendingPublications(self archive=None):
        """Create some pending publications."""
        if archive is None:
            archive = getUtility(
                IDistributionSet).getByName('ubuntu').main_archive
        foo_source = self.stp.getPubSource("foo")
        foo_binaries = self.stp.getPubBinaries(pub_source=foo_source)
        return (foo_source, foo_binaries)

    def assertPublishingStatus(self, publications, status):
        """Assert that the supplied publications have the supplied status."""
        for pub in publications:
            self.assertEqual(pub.status, status)

    def testAcceptCopyArchives(self):
        """Test that publications in a copy archive are accepted properly."""
        # Publish some pending packages in a copy archive.
        copy_archive = self.makeArchive(purpose=ArchivePurpose.COPY)
        foo_source, foo_binaries = self.createPendingPublications(
            archive=copy_archive)
        # Also publish some source in the main archive.
        main_source = self.createPendingPublications()

        # Assert everything's pending.
        publications = foo_source
        publications.extend(foo_binaries)
        self.assertPublishingStatus(
            publications, PackagePublishingStatus.PENDING)
        self.assertEqual(main_source, PackagePublishingStatus.PENDING)

        # Accept the publications.
        script = self.getScript(['--copy-archives'])
        Store.of(foo_source).flush()
        self.layer.switchDbUser(self.dbuser)
        script.main()

        # Check publishing status.
        self.assertPublishingStatus(
            publications, PackagePublishingStatus.PUBLISHED)

        # Package in main archive should not change.
        self.assertEqual(main_source, PackagePublishingStatus.PENDING)

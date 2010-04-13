# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test process-accepted.py"""

from cStringIO import StringIO

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.scripts import QuietFakeLogger
from canonical.launchpad.webapp.errorlog import ErrorReportingUtility
from canonical.testing import LaunchpadZopelessLayer

from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.series import SeriesStatus
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

    def createWaitingAcceptancePackage(self, archive=None, distroseries=None,
            sourcename=None):
        """Create some pending publications."""
        if archive is None:
            archive = getUtility(
                IDistributionSet).getByName('ubuntutest').main_archive
        if sourcename is None:
            sourcename = self.test_package_name
        return self.stp.getPubSource(
            archive=archive, sourcename=sourcename, distroseries=distroseries,
            spr_only=True)

    def testRobustness(self):
        """Test that a broken package doesn't block the publication of other 
        packages."""
        # Attempt to upload one source to a frozen series
        distroseries = self.factory.makeDistroSeries(
            distribution=getUtility(IDistributionSet).getByName('ubuntutest'))
        broken_source = self.createWaitingAcceptancePackage(
            distroseries=distroseries, sourcename="notaccepted")
        distroseries.status = SeriesStatus.SUPPORTED
        # Also upload some other things
        other_source = self.createWaitingAcceptancePackage()
        script = self.getScript([])
        script.main()

        # The other source should be published now
        published_main = self.stp.ubuntutest.main_archive.getPublishedSources(
            name=self.test_package_name)
        self.assertEqual(published_main.count(), 1)

        # And an oops should be filed for the first
        error_utility = ErrorReportingUtility()
        error_report = error_utility.getLastOopsReport()
        fp = StringIO()
        error_report.write(fp)
        error_text = fp.getvalue()
        self.failUnless("error-explanation=Failure processing queue_item" 
            in error_text)

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


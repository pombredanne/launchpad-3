# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test process-accepted.py"""

from cStringIO import StringIO

from debian.deb822 import Changes

from canonical.config import config
from canonical.launchpad.webapp.errorlog import ErrorReportingUtility
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.registry.interfaces.series import SeriesStatus
from lp.services.log.logger import BufferLogger
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.soyuz.scripts.processaccepted import (
    get_bugs_from_changes_file,
    ProcessAccepted,
    )
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
        self.distro = self.factory.makeDistribution()

    def getScript(self, test_args=None):
        """Return a ProcessAccepted instance."""
        if test_args is None:
            test_args = []
        test_args.append(self.distro.name)
        script = ProcessAccepted("process accepted", test_args=test_args)
        script.logger = BufferLogger()
        script.txn = self.layer.txn
        return script

    def createWaitingAcceptancePackage(self, distroseries, archive=None,
                                       sourcename=None):
        """Create some pending publications."""
        if archive is None:
            archive = self.distro.main_archive
        if sourcename is None:
            sourcename = self.test_package_name
        return self.stp.getPubSource(
            archive=archive, sourcename=sourcename, distroseries=distroseries,
            spr_only=True)

    def test_robustness(self):
        """Test that a broken package doesn't block the publication of other
        packages."""
        # Attempt to upload one source to a supported series
        # The record is created first and then the status of the series
        # is changed from DEVELOPMENT to SUPPORTED, otherwise it's impossible
        # to create the record
        distroseries = self.factory.makeDistroSeries(distribution=self.distro)
        broken_source = self.createWaitingAcceptancePackage(
            distroseries=distroseries, sourcename="notaccepted")
        distroseries.status = SeriesStatus.SUPPORTED
        # Also upload some other things
        other_distroseries = self.factory.makeDistroSeries(
            distribution=self.distro)
        other_source = self.createWaitingAcceptancePackage(
            distroseries=other_distroseries)
        script = self.getScript([])
        self.layer.txn.commit()
        self.layer.switchDbUser(self.dbuser)
        script.main()

        # The other source should be published now
        published_main = self.distro.main_archive.getPublishedSources(
            name=self.test_package_name)
        self.assertEqual(published_main.count(), 1)

        # And an oops should be filed for the first
        error_utility = ErrorReportingUtility()
        error_report = error_utility.getLastOopsReport()
        fp = StringIO()
        error_report.write(fp)
        error_text = fp.getvalue()
        expected_error = "error-explanation=Failure processing queue_item"
        self.assertTrue(expected_error in error_text)

    def test_accept_copy_archives(self):
        """Test that publications in a copy archive are accepted properly."""
        # Upload some pending packages in a copy archive.
        distroseries = self.factory.makeDistroSeries(distribution=self.distro)
        copy_archive = self.factory.makeArchive(
            distribution=self.distro, purpose=ArchivePurpose.COPY)
        copy_source = self.createWaitingAcceptancePackage(
            archive=copy_archive, distroseries=distroseries)
        # Also upload some stuff in the main archive.
        main_source = self.createWaitingAcceptancePackage(
            distroseries=distroseries)

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
        published_main = self.distro.main_archive.getPublishedSources(
            name=self.test_package_name)
        self.assertEqual(published_main.count(), 0)

        # Check the copy archive source was accepted.
        [published_copy] = copy_archive.getPublishedSources(
            name=self.test_package_name)
        self.assertEqual(
            published_copy.status, PackagePublishingStatus.PENDING)
        self.assertEqual(copy_source, published_copy.sourcepackagerelease)


class TestBugsFromChangesFile(TestCaseWithFactory):
    """Test get_bugs_from_changes_file."""

    layer = LaunchpadZopelessLayer
    dbuser = config.uploadqueue.dbuser

    def setUp(self):
        super(TestBugsFromChangesFile, self).setUp()
        self.changes = Changes({
            'Format': '1.8',
            'Source': 'swat',
            })

    def getBugs(self):
        """Serialize self.changes and use get_bugs_from_changes_file to
        extract bugs from it.
        """
        stream = StringIO()
        self.changes.dump(stream)
        stream.seek(0)
        return get_bugs_from_changes_file(stream)

    def test_no_bugs(self):
        # An empty list is returned if there are no bugs
        # mentioned.
        self.assertEquals([], self.getBugs())

    def test_invalid_bug_id(self):
        # Invalid bug ids (i.e. containing non-digit characters) are ignored.
        self.changes["Launchpad-Bugs-Fixed"] = "bla"
        self.assertEquals([], self.getBugs())

    def test_unknown_bug_id(self):
        # Unknown bug ids are ignored.
        self.changes["Launchpad-Bugs-Fixed"] = "45120"
        self.assertEquals([], self.getBugs())

    def test_valid_bug(self):
        # For valid bug ids the bug object is returned.
        bug = self.factory.makeBug()
        self.changes["Launchpad-Bugs-Fixed"] = "%d" % bug.id
        self.assertEquals([bug], self.getBugs())

    def test_case_sensitivity(self):
        # The spelling of Launchpad-Bugs-Fixed is case-insensitive.
        bug = self.factory.makeBug()
        self.changes["LaUnchpad-Bugs-fixed"] = "%d" % bug.id
        self.assertEquals([bug], self.getBugs())

    def test_multiple_bugs(self):
        # Multiple bug ids can be specified, separated by spaces.
        bug1 = self.factory.makeBug()
        bug2 = self.factory.makeBug()
        self.changes["Launchpad-Bugs-Fixed"] = "%d invalid %d" % (
            bug1.id, bug2.id)
        self.assertEquals([bug1, bug2], self.getBugs())

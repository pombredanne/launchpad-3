# Copyright 2006 Canonical Ltd.  All rights reserved.
"""ftpmaster facilities tests."""

__metaclass__ = type

from unittest import TestLoader
import shutil
import subprocess
import os
import sys

from zope.component import getUtility

from canonical.config import config
from canonical.testing import LaunchpadZopelessLayer
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.launchpad.database.component import ComponentSelection
from canonical.launchpad.interfaces import (
    IDistributionSet, IComponentSet, ISectionSet)
from canonical.launchpad.scripts.ftpmaster import (
    ArchiveOverrider, ArchiveOverriderError, ArchiveCruftChecker,
    ArchiveCruftCheckerError)
from canonical.lp.dbschema import (
    PackagePublishingPocket, PackagePublishingPriority)

# XXX cprov 2006-05-15: {create, remove}TestArchive functions should be
# moved to the publisher test domain as soon as we have it.
def createTestArchive():
    """Creates a fresh test archive based on sampledata."""
    script = os.path.join(config.root, "scripts", "publish-distro.py")
    process = subprocess.Popen([sys.executable, script, "-C", "-q",
                                "-d", 'ubuntutest'],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    garbage = process.stderr.read()
    garbage = process.stdout.read()
    return process.wait()

def removeTestArchive():
    """Remove the entire test archive directory from the filesystem."""
    shutil.rmtree("/var/tmp/archive/")


class MockLogger:
    """Local log facility """
    def __init__(self):
        self.logs = []

    def read(self):
        """Return printable log contents and reset current log."""
        content = "\n".join(self.logs)
        self.logs = []
        return content

    def debug(self, txt):
        self.logs.append("DEBUG: %s" % txt)

    def info(self, txt):
        self.logs.append("INFO: %s" % txt)

    def error(self, txt):
        self.logs.append("ERROR: %s" % txt)

    def warn(self, txt):
        self.logs.append("WARN: %s" % txt)


class TestArchiveOverrider(LaunchpadZopelessTestCase):
    layer = LaunchpadZopelessLayer
    dbuser = 'lucille'

    def setUp(self):
        """Setup the test environment and retrieve useful instances."""
        LaunchpadZopelessTestCase.setUp(self)
        self.log = MockLogger()

        self.ubuntu = getUtility(IDistributionSet)['ubuntu']
        self.hoary = self.ubuntu['hoary']
        self.component_main = getUtility(IComponentSet)['main']
        self.section_base = getUtility(ISectionSet)['base']

        # Allow commercial in warty and hoary.
        commercial_component = getUtility(IComponentSet)['commercial']
        self.ubuntu_warty = self.ubuntu['warty']
        self.ubuntu_hoary = self.ubuntu['hoary']
        ComponentSelection(distroseries=self.ubuntu_warty,
                           component=commercial_component)
        ComponentSelection(distroseries=self.ubuntu_hoary,
                           component=commercial_component)

    def test_initialize_success(self):
        """Test ArchiveOverrider initialization process.

        Check if the correct attributes are built after initialization.
        """
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary',
            component_name='main', section_name='base', priority_name='extra')
        changer.initialize()
        self.assertEqual(self.ubuntu, changer.distro)
        self.assertEqual(self.hoary, changer.distroseries)
        self.assertEqual(PackagePublishingPocket.RELEASE, changer.pocket)
        self.assertEqual(self.component_main, changer.component)
        self.assertEqual(self.section_base, changer.section)
        self.assertEqual(PackagePublishingPriority.EXTRA, changer.priority)
        self.log.read()

    def test_initialize_only_component(self):
        """Test initialize() only for changing component.

        Check if the correct attribute is built and it doesn't raise
        any exception.
        """
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary',
            component_name='main')
        changer.initialize()
        self.assertEqual(self.component_main, changer.component)
        self.assertEqual(None, changer.section)
        self.assertEqual(None, changer.priority)
        self.log.read()

    def test_initialize_only_section(self):
        """Test initialize() only for changing section.

        Check if the correct attribute is built and it doesn't raise
        any exception.
        """
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary',
            section_name='base')
        changer.initialize()
        self.assertEqual(None, changer.component)
        self.assertEqual(self.section_base, changer.section)
        self.assertEqual(None, changer.priority)
        self.log.read()

    def test_initialize_only_priority(self):
        """Test initialize() only for changing section.

        Check if the correct attribute is built and it doesn't raise
        any exception.
        """
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary',
            priority_name='extra')
        changer.initialize()
        self.assertEqual(None, changer.component)
        self.assertEqual(None, changer.section)
        self.assertEqual(PackagePublishingPriority.EXTRA, changer.priority)
        self.log.read()

    def test_initialize_missing_args(self):
        """ArchiveOverrider should raise if no required attributes are passed"""
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary')
        self.assertRaises(
            ArchiveOverriderError, changer.initialize)
        self.log.read()

    def test_initialize_broken_distro(self):
        """ArchiveOverrider should raise on a unknown distribution name"""
        changer = ArchiveOverrider(
            self.log, distro_name='foo', suite='hoary',
            component_name='main', section_name='base', priority_name='extra')
        self.assertRaises(
            ArchiveOverriderError, changer.initialize)
        self.log.read()

    def test_initialize_broken_suite(self):
        """ArchiveOverrider should raise if no a unknown suite name"""
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='bar',
            component_name='main', section_name='base', priority_name='extra')
        self.assertRaises(
            ArchiveOverriderError, changer.initialize)
        self.log.read()

    def test_initialize_full_suite(self):
        """ArchiveOverrider accepts full suite name.

        It split suite name into 'distroseries' and 'pocket' attributes after
        initialize().
        """
        # XXX cprov 2006-04-24: change-override API doesn't handle pockets
        # properly yet. It may need a deep redesign on how we model the
        # packages meta-classes (SourcePackage, DistributionSourcePackage,
        # etc)
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary',
            component_name='main', section_name='base', priority_name='extra')
        changer.initialize()
        self.assertEqual(PackagePublishingPocket.RELEASE, changer.pocket)

        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary-updates',
            component_name='main', section_name='base', priority_name='extra')
        changer.initialize()
        self.assertEqual(PackagePublishingPocket.UPDATES, changer.pocket)

        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary-foo',
            component_name='main', section_name='base', priority_name='extra')
        self.assertRaises(
            ArchiveOverriderError, changer.initialize)
        self.log.read()

    def test_initialize_broken_component(self):
        """Raises on a unknown/unselected component name."""
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary',
            component_name='baz', section_name='base', priority_name='extra')
        self.assertRaises(
            ArchiveOverriderError, changer.initialize)
        self.log.read()

    def test_initialize_broken_section(self):
        """Raises on a unknown/unselected section name."""
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary',
            component_name='main', section_name='bozo', priority_name='extra')
        self.assertRaises(
            ArchiveOverriderError, changer.initialize)
        self.log.read()

    def test_initialize_broken_priority(self):
        """Raises on a unknown priority  name."""
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary',
            component_name='main', section_name='base', priority_name='bingo')
        self.assertRaises(
            ArchiveOverriderError, changer.initialize)
        self.log.read()

    def test_processSourceChange_success(self):
        """Check processSourceChange method call.

        It simply wraps changeOverride method on
        IDistroSeriesSourcePackageRelease, which is already tested in place.
        Inspect the log to verify if the correct source was picked and correct
        arguments was passed.
        """
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='warty',
            component_name='main', section_name='base', priority_name='extra')
        changer.initialize()
        changer.processSourceChange('mozilla-firefox')
        self.assertEqual(
            self.log.read(),
            "INFO: Override Component to: 'main'\n"
            "INFO: Override Section to: 'base'\n"
            "INFO: Override Priority to: 'EXTRA'\n"
            "INFO: 'mozilla-firefox/main/base' source overridden")

    def test_processSourceChange_with_changed_archive(self):
        """Check processSourceChange method call with an archive change.

        Changing the component to 'commercial' will result in the archive
        changing on the publishing record.  This is disallowed.
        """
        # Apply the override.
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='warty',
            component_name='commercial', section_name='base',
            priority_name='extra')
        changer.initialize()
        self.assertRaises(
            ArchiveOverriderError, changer.processSourceChange,
            'mozilla-firefox')

    def test_processSourceChange_error(self):
        """processSourceChange warns the user about an unpublished source.

        Inspect the log messages.
        """
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary',
            component_name='main', section_name='base', priority_name='extra')
        changer.initialize()
        changer.processSourceChange('mozilla-firefox')
        self.assertEqual(
            self.log.read(),
            "INFO: Override Component to: 'main'\n"
            "INFO: Override Section to: 'base'\n"
            "INFO: Override Priority to: 'EXTRA'\n"
            "ERROR: 'mozilla-firefox' source isn't published in hoary")

    def test_processBinaryChange_success(self):
        """Check if processBinaryChange() picks the correct binary.

        It simply wraps changeOverride method on
        IDistroArchSeriesBinaryPackage, which is already tested in place.
        Inspect the log messages, check if the correct binary was picked
        and correct argument was passed.
        """
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary',
            component_name='main', section_name='base', priority_name='extra')
        changer.initialize()
        changer.processBinaryChange('pmount')
        self.assertEqual(
            self.log.read(),
            "INFO: Override Component to: 'main'\n"
            "INFO: Override Section to: 'base'\n"
            "INFO: Override Priority to: 'EXTRA'\n"
            "INFO: 'pmount/main/base/EXTRA' binary overridden in hoary/hppa\n"
            "INFO: 'pmount/universe/editors/IMPORTANT' binary "
                "overridden in hoary/i386")

    def test_processBinaryChange_with_changed_archive(self):
        """Check processBinaryChange method call with an archive change.

        Changing the component to 'commercial' will result in the archive
        changing.  This is disallowed.
        """
        # Apply the override.
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary',
            component_name='commercial', section_name='base',
            priority_name='extra')
        changer.initialize()
        self.assertRaises(
            ArchiveOverriderError, changer.processBinaryChange, 'pmount')

    def test_processBinaryChange_error(self):
        """processBinaryChange warns the user about an unpublished binary.

        Inspect the log messages.
        """
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='warty',
            component_name='main', section_name='base', priority_name='extra')
        changer.initialize()
        changer.processBinaryChange('evolution')
        self.assertEqual(
            self.log.read(),
            "INFO: Override Component to: 'main'\n"
            "INFO: Override Section to: 'base'\n"
            "INFO: Override Priority to: 'EXTRA'\n"
            "ERROR: 'evolution' binary not found.")

    def test_processChildrenChange_success(self):
        """processChildrenChanges, modify the source and its binary children.

        It simply used the local processChangeSource on a passed name and
        processChangeBinary on each retrieved binary child.
        Inspect the log and to ensure we are passing correct arguments and
        picking the correct source.
        """
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='warty',
            component_name='main', section_name='base',
            priority_name='extra')
        changer.initialize()
        changer.processChildrenChange('mozilla-firefox')
        self.assertEqual(
            self.log.read(),
            "INFO: Override Component to: 'main'\n"
            "INFO: Override Section to: 'base'\n"
            "INFO: Override Priority to: 'EXTRA'\n"
            "INFO: 'mozilla-firefox/main/base/IMPORTANT' "
                "binary overridden in warty/i386\n"
            "INFO: 'mozilla-firefox/main/base/EXTRA' "
                "binary overridden in warty/hppa\n"
            "INFO: 'mozilla-firefox-data/main/base/EXTRA' "
                "binary overridden in warty/hppa\n"
            "INFO: 'mozilla-firefox-data/main/base/EXTRA' "
                "binary overridden in warty/i386")

    def test_processChildrenChange_error(self):
        """processChildrenChange warns the user about an unpublished source.

        Inspect the log messages.
        """
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='warty',
            component_name='main', section_name='base',
            priority_name='extra')
        changer.initialize()
        changer.processChildrenChange('pmount')
        self.assertEqual(
            self.log.read(),
            "INFO: Override Component to: 'main'\n"
            "INFO: Override Section to: 'base'\n"
            "INFO: Override Priority to: 'EXTRA'\n"
            "ERROR: 'pmount' source isn't published in warty")

        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary',
            component_name='main', section_name='base',
            priority_name='extra')
        changer.initialize()
        changer.processChildrenChange('pmount')
        self.assertEqual(
            self.log.read(),
            "INFO: Override Component to: 'main'\n"
            "INFO: Override Section to: 'base'\n"
            "INFO: Override Priority to: 'EXTRA'\n"
            "WARN: 'pmount' has no binaries published in hoary")


class TestArchiveCruftChecker(LaunchpadZopelessTestCase):
    layer = LaunchpadZopelessLayer
    dbuser = 'lucille'

    def setUp(self):
        """Setup the test environment.

        Retrieve useful instances and create a test archive.
        """
        LaunchpadZopelessTestCase.setUp(self)
        self.log = MockLogger()

        self.ubuntutest = getUtility(IDistributionSet)['ubuntutest']
        self.breezy_autotest = self.ubuntutest['breezy-autotest']
        self.archive_path = "/var/tmp/archive"
        createTestArchive()

    def tearDown(self):
        """Clean up test environment and remove the test archive."""
        LaunchpadZopelessTestCase.tearDown(self)
        removeTestArchive()

    def test_initialize_success(self):
        """Test ArchiveCruftChecker initialization process.

        Check if the correct attributes are built after initialization.
        """
        checker = ArchiveCruftChecker(
            self.log, distribution_name='ubuntutest', suite='breezy-autotest',
            archive_path=self.archive_path)
        checker.initialize()
        self.assertEqual(self.ubuntutest, checker.distro)
        self.assertEqual(self.breezy_autotest, checker.distroseries)
        self.assertEqual(PackagePublishingPocket.RELEASE, checker.pocket)
        self.assertEqual(0, len(checker.nbs_to_remove))
        self.assertEqual(0, len(checker.real_nbs))
        self.assertEqual(0, len(checker.dubious_nbs))
        self.assertEqual(0, len(checker.bin_pkgs))
        self.assertEqual(0, len(checker.arch_any))
        self.assertEqual(0, len(checker.source_versions))
        self.assertEqual(0, len(checker.source_binaries))
        self.log.read()

    def test_initialize_unknown_suite(self):
        """ArchiveCruftChecker should raise on an unknown suite."""
        checker = ArchiveCruftChecker(
            self.log, distribution_name='ubuntu', suite='misarable',
            archive_path=self.archive_path)
        self.assertRaises(
            ArchiveCruftCheckerError, checker.initialize)
        self.log.read()

    def test_initialize_unknown_distribution(self):
        """ArchiveCruftChecker should raise on an unknown distribution."""
        checker = ArchiveCruftChecker(
            self.log, distribution_name='foobuntu', suite='breezy-autotest',
            archive_path=self.archive_path)
        self.assertRaises(
            ArchiveCruftCheckerError, checker.initialize)
        self.log.read()

    def test_initialize_no_distro_in_archive(self):
        """ArchiveCruftChecker should raise on the absence of distribution."""
        checker = ArchiveCruftChecker(
            self.log, distribution_name='ubuntu', suite='breezy-autotest',
            archive_path=self.archive_path)
        self.assertRaises(
            ArchiveCruftCheckerError, checker.initialize)
        self.log.read()


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

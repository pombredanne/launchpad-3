# Copyright 2006 Canonical Ltd.  All rights reserved.
"""ftpmaster facilities tests."""

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.interfaces.component import IComponentSet
from canonical.launchpad.interfaces.distribution import IDistributionSet
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.interfaces.person import IPersonSet
from canonical.launchpad.interfaces.publishing import (
    PackagePublishingPocket, PackagePublishingPriority,
    PackagePublishingStatus)
from canonical.launchpad.interfaces.section import ISectionSet
from canonical.launchpad.scripts import FakeLogger
from canonical.launchpad.scripts.changeoverride import (
    ChangeOverride, ArchiveOverriderError)
from canonical.launchpad.scripts.ftpmasterbase import SoyuzScriptError
from canonical.launchpad.tests.test_publishing import SoyuzTestPublisher
from canonical.testing import LaunchpadZopelessLayer


class LocalLogger(FakeLogger):
    """Local log facility """

    def __init__(self):
        self.logs = []

    def read(self):
        """Return printable log contents and reset current log."""
        content = "\n".join(self.logs)
        self.logs = []
        return content

    def message(self, prefix, *stuff, **kw):
        self.logs.append("%s %s" % (prefix, ' '.join(stuff)))


class TestChangeOverride(unittest.TestCase):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        """ """
        self.ubuntu = getUtility(IDistributionSet)['ubuntu']
        self.warty = self.ubuntu.getSeries('warty')
        self.warty_i386 = self.warty['i386']
        self.warty_hppa = self.warty['hppa']

        fake_chroot = getUtility(ILibraryFileAliasSet)[1]
        self.warty_i386.addOrUpdateChroot(fake_chroot)
        self.warty_hppa.addOrUpdateChroot(fake_chroot)

        self.test_publisher = SoyuzTestPublisher()
        self.test_publisher.person = getUtility(
            IPersonSet).getByName("name16")

    def getChanger(self, sourcename='mozilla-firefox', sourceversion=None,
                   distribution='ubuntu', suite='warty',
                   arch_tag=None, component=None, section=None, priority=None,
                   source_and_binary=False, binary_and_source=False,
                   source_only=False, confirm_all=True):
        """Return a PackageCopier instance.

        Allow tests to use a set of default options to ChangeOverride.
        """
        test_args = [
            '-s', suite,
            '-d', distribution,
            ]

        if confirm_all:
            test_args.append('-y')

        if source_and_binary:
            test_args.append('-S')

        if binary_and_source:
            test_args.append('-B')

        if source_only:
            test_args.append('-t')

        if sourceversion is not None:
            test_args.extend(['-e', sourceversion])

        if arch_tag is not None:
            test_args.extend(['-a', arch_tag])

        if component is not None:
            test_args.extend(['-c', component])

        if section is not None:
            test_args.extend(['-x', section])

        if priority is not None:
            test_args.extend(['-p', priority])

        test_args.append(sourcename)

        changer = ChangeOverride(
            name='change-override', test_args=test_args)
        changer.logger = LocalLogger()
        changer.setupLocation()
        return changer

    def test_changeoveride_initialize(self):
        """ChangeOverride initialization process.

        Check if the correct attributes are built after initialization.
        """
        changer = self.getChanger(
            component="main", section="base", priority="extra")

        # Processed location inherited from SoyuzScript.
        self.assertEqual(
            self.ubuntu, changer.location.distribution)
        self.assertEqual(
            self.warty, changer.location.distroseries)
        self.assertEqual(
            PackagePublishingPocket.RELEASE, changer.location.pocket)

        # Resolved override values.
        self.assertEqual(
            getUtility(IComponentSet)['main'], changer.component)
        self.assertEqual(
            getUtility(ISectionSet)['base'], changer.section)
        self.assertEqual(
            PackagePublishingPriority.EXTRA, changer.priority)

    def assertCurrentBinary(self, distroarchseries, name, version,
                            component_name, section_name, priority_name):
        """Assert if the current binary publication matches the given data."""
        dasbpr = distroarchseries.getBinaryPackage(name)[version]
        pub = dasbpr.current_publishing_record
        self.assertTrue(pub.status.name in ['PUBLISHED', 'PENDING'])
        self.assertEqual(pub.component.name, component_name)
        self.assertEqual(pub.section.name, section_name)
        self.assertEqual(pub.priority.name, priority_name)

    def assertCurrentSource(self, distroseries, name, version,
                            component_name, section_name):
        """Assert if the current source publication matches the given data."""
        dsspr = distroseries.getSourcePackage(name)[version]
        pub = dsspr.current_published
        self.assertTrue(pub.status.name in ['PUBLISHED', 'PENDING'])
        self.assertEqual(pub.component.name, component_name)
        self.assertEqual(pub.section.name, section_name)

    def test_changeoverride_operations(self):
        """Check if `IArchivePublisher.changeOverride` is wrapped correctly.

        Inspect the log to verify if the correct source and/or binaries were
        picked and correct arguments was passed.
        """
        # Setup publishing context.
        # 'boingo' source and 'boingo-bin' binaries in warty (i386 & hppa).
        source = self.test_publisher.getPubSource(
            sourcename="boingo", version='1.0', distroseries=self.warty,
            component='universe', section='web')
        binaries = self.test_publisher.getPubBinaries(
            'boingo-bin', pub_source=source, distroseries=self.warty)

        changer = self.getChanger(
            suite="warty", component="main", section="base", priority='extra')
        self.assertEqual(
            changer.logger.read(),
            "INFO Override Component to: 'main'\n"
            "INFO Override Section to: 'base'\n"
            "INFO Override Priority to: 'EXTRA'")

        # Override the source.
        changer.processSourceChange('boingo')
        self.assertEqual(
            changer.logger.read(),
            "INFO 'boingo - 1.0/universe/web' source overridden")
        self.assertCurrentSource(
            self.warty, 'boingo', '1.0', 'main', 'base')

        # Override the binaries.
        changer.processBinaryChange('boingo-bin')
        self.assertEqual(
            changer.logger.read(),
            "INFO 'boingo-bin-1.0/universe/web/STANDARD' binary "
                "overridden in warty/hppa\n"
            "INFO 'boingo-bin-1.0/universe/web/STANDARD' binary "
                "overridden in warty/i386")
        self.assertCurrentBinary(
            self.warty_i386, 'boingo-bin', '1.0', 'main', 'base', 'EXTRA')
        self.assertCurrentBinary(
            self.warty_hppa, 'boingo-bin', '1.0', 'main', 'base', 'EXTRA')

        # Override the source children.
        changer.processChildrenChange('boingo')
        self.assertEqual(
            changer.logger.read(),
            "INFO 'boingo-bin-1.0/main/base/EXTRA' remained the same\n"
            "INFO 'boingo-bin-1.0/main/base/EXTRA' remained the same")
        self.assertCurrentBinary(
            self.warty_i386, 'boingo-bin', '1.0', 'main', 'base', 'EXTRA')
        self.assertCurrentBinary(
            self.warty_hppa, 'boingo-bin', '1.0', 'main', 'base', 'EXTRA')

    def test_changeoverride_no_change(self):
        """Override source and/or binary already in the desired state.

        Nothing is done and the event is logged.
        """
        source = self.test_publisher.getPubSource(
            sourcename="boingo", version='1.0', distroseries=self.warty,
            component='main', section='web')
        binaries = self.test_publisher.getPubBinaries(
            'boingo-bin', pub_source=source, distroseries=self.warty)

        changer = self.getChanger(
            suite="warty", component="main", section="web",
            priority='standard')

        self.assertEqual(
            changer.logger.read(),
            "INFO Override Component to: 'main'\n"
            "INFO Override Section to: 'web'\n"
            "INFO Override Priority to: 'STANDARD'")

        changer.processSourceChange('boingo')
        self.assertEqual(
            changer.logger.read(),
            "INFO 'boingo - 1.0/main/web' remained the same")

        self.assertCurrentSource(
            self.warty, 'boingo', '1.0', 'main', 'web')

        changer.processBinaryChange('boingo-bin')
        self.assertEqual(
            changer.logger.read(),
            "INFO 'boingo-bin-1.0/main/web/STANDARD' remained the same\n"
            "INFO 'boingo-bin-1.0/main/web/STANDARD' remained the same")

        self.assertCurrentBinary(
            self.warty_i386, 'boingo-bin', '1.0', 'main', 'web', 'STANDARD')
        self.assertCurrentBinary(
            self.warty_hppa, 'boingo-bin', '1.0', 'main', 'web', 'STANDARD')

    def test_overrides_with_changed_archive(self):
        """Overrides resulting in archive changes are not allowed.

        Changing the component to 'partner' will result in the archive
        changing on the publishing record.
        """
        binaries = self.test_publisher.getPubBinaries(
            'boingo-bin', distroseries=self.warty)

        changer = self.getChanger(
            component="partner", section="base", priority="extra")

        self.assertRaises(
            ArchiveOverriderError, changer.processSourceChange, 'boingo')
        self.assertRaises(
            ArchiveOverriderError, changer.processBinaryChange, 'boingo-bin')
        self.assertRaises(
            ArchiveOverriderError, changer.processChildrenChange, 'boingo')

    def test_target_publication_not_found(self):
        """Raises SoyuzScriptError when a source was not found."""
        changer = self.getChanger(
            component="main", section="base", priority="extra")

        self.assertRaises(
            SoyuzScriptError, changer.processSourceChange, 'foobar')
        self.assertRaises(
            SoyuzScriptError, changer.processBinaryChange, 'biscuit')
        self.assertRaises(
            SoyuzScriptError, changer.processChildrenChange, 'cookie')

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

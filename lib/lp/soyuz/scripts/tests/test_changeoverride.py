# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""`ChangeOverride` script class tests."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.log.logger import BufferLogger
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.enums import PackagePublishingPriority
from lp.soyuz.interfaces.section import ISectionSet
from lp.soyuz.scripts.changeoverride import (
    ArchiveOverriderError,
    ChangeOverride,
    )
from lp.soyuz.scripts.ftpmasterbase import SoyuzScriptError
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher


class TestChangeOverride(unittest.TestCase):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        """`ChangeOverride` test environment setup.

        Setup a `SoyuzTestPublisher` instance and ubuntu/warty/{i386, hppa}.
        """
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

    def getChanger(self, package_name='mozilla-firefox', package_version=None,
                   distribution='ubuntu', suite='warty',
                   arch_tag=None, component=None, section=None, priority=None,
                   source_and_binary=False, binary_and_source=False,
                   source_only=False, confirm_all=True):
        """Return a `ChangeOverride` instance.

        Allow tests to use a set of default options.
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

        if package_version is not None:
            test_args.extend(['-e', package_version])

        if arch_tag is not None:
            test_args.extend(['-a', arch_tag])

        if component is not None:
            test_args.extend(['-c', component])

        if section is not None:
            test_args.extend(['-x', section])

        if priority is not None:
            test_args.extend(['-p', priority])

        test_args.extend(package_name.split())

        changer = ChangeOverride(
            name='change-override', test_args=test_args)
        changer.logger = BufferLogger()
        changer.setupLocation()
        return changer

    def test_changeoverride_initialize(self):
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

        # Overrides initialization output.
        self.assertEqual(
            changer.logger.getLogBuffer(),
            "INFO Override Component to: 'main'\n"
            "INFO Override Section to: 'base'\n"
            "INFO Override Priority to: 'EXTRA'\n")

    def patchedChanger(self, source_only=False, source_and_binary=False,
                       binary_and_source=False, package_name='foo'):
        """Return a patched `ChangeOverride` object.

        All operations are modified to allow test tracing.
        """
        changer = self.getChanger(
            component="main", section="base", priority="extra",
            source_only=source_only, source_and_binary=source_and_binary,
            binary_and_source=binary_and_source, package_name=package_name)

        # Patched override operations.
        def fakeProcessSourceChange(name):
            changer.logger.info("Source change for '%s'" % name)

        def fakeProcessBinaryChange(name):
            changer.logger.info("Binary change for '%s'" % name)

        def fakeProcessChildrenChange(name):
            changer.logger.info("Children change for '%s'" % name)

        # Patch the override operations.
        changer.processSourceChange = fakeProcessSourceChange
        changer.processBinaryChange = fakeProcessBinaryChange
        changer.processChildrenChange = fakeProcessChildrenChange

        # Consume the initialization logging.
        changer.logger.clearLogBuffer()

        return changer

    def test_changeoverride_modes(self):
        """Check `ChangeOverride` modes.

        Confirm the expected behaviour of the change-override modes:

         * Binary-only: default mode, only override binaries exactly matching
              the given name;
         * Source-only: activated via '-t', override only the matching source;
         * Binary-and-source: activated via '-B', override source and binaries
              exactly matching the given name.
         * Source-and-binaries: activated via '-S', override the source
              matching the given name and the binaries built from it.
        """
        changer = self.patchedChanger()
        changer.mainTask()
        self.assertEqual(
            changer.logger.getLogBufferAndClear(),
            "INFO Binary change for 'foo'\n")

        changer = self.patchedChanger(source_only=True)
        changer.mainTask()
        self.assertEqual(
            changer.logger.getLogBufferAndClear(),
            "INFO Source change for 'foo'\n")

        changer = self.patchedChanger(binary_and_source=True)
        changer.mainTask()
        self.assertEqual(
            changer.logger.getLogBufferAndClear(),
            "INFO Source change for 'foo'\n"
            "INFO Binary change for 'foo'\n")

        changer = self.patchedChanger(source_and_binary=True)
        changer.mainTask()
        self.assertEqual(
            changer.logger.getLogBufferAndClear(),
            "INFO Source change for 'foo'\n"
            "INFO Children change for 'foo'\n")

    def test_changeoverride_multiple_targets(self):
        """`ChangeOverride` can operate on multiple targets.

        It will perform the defined operation for all given command-line
        arguments.
        """
        changer = self.patchedChanger(package_name='foo bar baz')
        changer.mainTask()
        self.assertEqual(
            changer.logger.getLogBufferAndClear(),
            "INFO Binary change for 'foo'\n"
            "INFO Binary change for 'bar'\n"
            "INFO Binary change for 'baz'\n")

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

    def _setupOverridePublishingContext(self):
        """Setup publishing context.

         * 'boingo_1.0' source PENDING in ubuntu/warty;
         * 'boingo-bin_1.0' binaries PENDING in warty i386 & hppa;
         * 'boingo-data' binaries PENDING in warty i386 & hppa.
        """
        source = self.test_publisher.getPubSource(
            sourcename="boingo", version='1.0', distroseries=self.warty)

        binaries = self.test_publisher.getPubBinaries(
            'boingo-bin', pub_source=source, distroseries=self.warty)

        build = binaries[0].binarypackagerelease.build
        other_binary = self.test_publisher.uploadBinaryForBuild(
            build, 'boingo-data')
        other_binary.version = '0.9'
        binaries.extend(
            self.test_publisher.publishBinaryInArchive(
                other_binary, source.archive))

    def test_changeoverride_operations(self):
        """Check if `IArchivePublisher.changeOverride` is wrapped correctly.

        `ChangeOverride` allow three types of override operations:

         * Source-only overrides: `processSourceChange`;
         * Binary-only overrides: `processBinaryChange`;
         * Source-children overrides: `processChildrenChange`;

        This test checks the expected behaviour for each of them.
        """
        self._setupOverridePublishingContext()

        changer = self.getChanger(
            component="universe", section="web", priority='extra')
        changer.logger.clearLogBuffer()

        # Override the source.
        changer.processSourceChange('boingo')
        self.assertEqual(
            changer.logger.getLogBufferAndClear(),
            "INFO 'boingo - 1.0/main/base' source overridden\n")
        self.assertCurrentSource(
            self.warty, 'boingo', '1.0', 'universe', 'web')

        # Override the binaries.
        changer.processBinaryChange('boingo-bin')
        self.assertEqual(
            changer.logger.getLogBufferAndClear(),
            "INFO 'boingo-bin-1.0/main/base/STANDARD' binary "
                "overridden in warty/hppa\n"
            "INFO 'boingo-bin-1.0/main/base/STANDARD' binary "
                "overridden in warty/i386\n")
        self.assertCurrentBinary(
            self.warty_i386, 'boingo-bin', '1.0', 'universe', 'web', 'EXTRA')
        self.assertCurrentBinary(
            self.warty_hppa, 'boingo-bin', '1.0', 'universe', 'web', 'EXTRA')

        # Override the source children.
        changer.processChildrenChange('boingo')
        self.assertEqual(
            changer.logger.getLogBufferAndClear(),
            "INFO 'boingo-bin-1.0/universe/web/EXTRA' remained the same\n"
            "INFO 'boingo-bin-1.0/universe/web/EXTRA' remained the same\n"
            "INFO 'boingo-data-0.9/main/base/STANDARD' binary "
                "overridden in warty/hppa\n"
            "INFO 'boingo-data-0.9/main/base/STANDARD' binary "
                "overridden in warty/i386\n")
        self.assertCurrentBinary(
            self.warty_i386, 'boingo-data', '0.9', 'universe', 'web', 'EXTRA')
        self.assertCurrentBinary(
            self.warty_hppa, 'boingo-data', '0.9', 'universe', 'web', 'EXTRA')

    def test_changeoverride_restricted_by_pocket(self):
        """`ChangeOverride` operation can be restricted by pocket.

        This behaviour is inherited from `SoyuzScript`.
        """
        # Create publications for 'boingo' source and 'boingo-bin' in
        # warty-security.
        source = self.test_publisher.getPubSource(
            sourcename="boingo", version='0.8', distroseries=self.warty,
            pocket=PackagePublishingPocket.SECURITY)
        self.test_publisher.getPubBinaries(
            'boingo-bin', pub_source=source, distroseries=self.warty,
            pocket=PackagePublishingPocket.SECURITY)

        # Create the default publishing context as 'noise' in order to
        # test if `ChangeOverride` filters it out properly.
        self._setupOverridePublishingContext()

        changer = self.getChanger(
            suite='warty-security', component="universe", section="web",
            priority='extra')
        changer.logger.clearLogBuffer()

        # Override the security source and its binaries.
        changer.processSourceChange('boingo')
        changer.processChildrenChange('boingo')
        self.assertEqual(
            changer.logger.getLogBufferAndClear(),
            "INFO 'boingo - 0.8/main/base' source overridden\n"
            "INFO 'boingo-bin-0.8/main/base/STANDARD' binary "
                "overridden in warty/hppa\n"
            "INFO 'boingo-bin-0.8/main/base/STANDARD' binary "
                "overridden in warty/i386\n")

        # Use a more precise lookup approach to reach and verify the
        # overridden security publications.
        security_source = changer.findLatestPublishedSource('boingo')
        self.assertEqual(
            security_source.sourcepackagerelease.version, '0.8')
        self.assertEqual(security_source.status.name, 'PENDING')
        self.assertEqual(security_source.pocket.name, 'SECURITY')
        self.assertEqual(security_source.component.name, 'universe')
        self.assertEqual(security_source.section.name, 'web')

        security_binaries = changer.findLatestPublishedBinaries('boingo-bin')
        for security_binary in security_binaries:
            self.assertEqual(
                security_binary.binarypackagerelease.version, '0.8')
            self.assertEqual(security_binary.status.name, 'PENDING')
            self.assertEqual(security_binary.pocket.name, 'SECURITY')
            self.assertEqual(security_binary.component.name, 'universe')
            self.assertEqual(security_binary.section.name, 'web')
            self.assertEqual(security_binary.priority.name, 'EXTRA')

    def test_changeoverride_restricted_by_version(self):
        """`ChangeOverride` operation can be restricted to a version.

        This behaviour is inherited from `SoyuzScript`.
        """
        self._setupOverridePublishingContext()
        changer = self.getChanger(
            component="universe", section="web", priority='extra',
            package_version='0.9')
        changer.logger.clearLogBuffer()

        # No 'boingo_0.9' source available.
        self.assertRaises(
            SoyuzScriptError, changer.processSourceChange, 'boingo')
        self.assertRaises(
            SoyuzScriptError, changer.processChildrenChange, 'boingo')

        # No 'boingo-bin_0.9' binary available.
        self.assertRaises(
            SoyuzScriptError, changer.processBinaryChange, 'boingo-bin')

        # 'boingo-data_0.9' is available and will be overridden.
        changer.processBinaryChange('boingo-data')
        self.assertEqual(
            changer.logger.getLogBufferAndClear(),
            "INFO 'boingo-data-0.9/main/base/STANDARD' binary "
                "overridden in warty/hppa\n"
            "INFO 'boingo-data-0.9/main/base/STANDARD' binary "
                "overridden in warty/i386\n")
        self.assertCurrentBinary(
            self.warty_i386, 'boingo-data', '0.9', 'universe', 'web', 'EXTRA')
        self.assertCurrentBinary(
            self.warty_hppa, 'boingo-data', '0.9', 'universe', 'web', 'EXTRA')

    def test_changeoverride_restricted_by_architecture(self):
        """`ChangeOverride` operation can be restricted to an architecture.

        This behaviour is inherited from `SoyuzScript`.
        """
        self._setupOverridePublishingContext()
        changer = self.getChanger(
            component="universe", section="web", priority='extra',
            arch_tag='i386')
        changer.logger.clearLogBuffer()

        # Source overrides are not affect by architecture restriction.
        changer.processSourceChange('boingo')
        self.assertEqual(
            changer.logger.getLogBufferAndClear(),
            "INFO 'boingo - 1.0/main/base' source overridden\n")
        self.assertCurrentSource(
            self.warty, 'boingo', '1.0', 'universe', 'web')

        # Binary overrides are restricted by architecture.
        changer.processBinaryChange('boingo-bin')
        self.assertEqual(
            changer.logger.getLogBufferAndClear(),
            "INFO 'boingo-bin-1.0/main/base/STANDARD' binary "
                "overridden in warty/i386\n")
        self.assertCurrentBinary(
            self.warty_i386, 'boingo-bin', '1.0', 'universe', 'web', 'EXTRA')
        self.assertCurrentBinary(
            self.warty_hppa, 'boingo-bin', '1.0', 'main', 'base', 'STANDARD')

        # Source-children overrides are also restricted by architecture.
        changer.processChildrenChange('boingo')
        self.assertEqual(
            changer.logger.getLogBufferAndClear(),
            "INFO 'boingo-bin-1.0/universe/web/EXTRA' remained the same\n"
            "INFO 'boingo-data-0.9/main/base/STANDARD' binary "
                "overridden in warty/i386\n")
        self.assertCurrentBinary(
            self.warty_i386, 'boingo-data', '0.9', 'universe', 'web', 'EXTRA')
        self.assertCurrentBinary(
            self.warty_hppa, 'boingo-data', '0.9', 'main', 'base', 'STANDARD')

    def test_changeoverride_no_change(self):
        """Override source and/or binary already in the desired state.

        Nothing is done and the event is logged.
        """
        self._setupOverridePublishingContext()

        changer = self.getChanger(
            component="main", section="base", priority='standard')
        changer.logger.clearLogBuffer()

        changer.processSourceChange('boingo')
        self.assertEqual(
            changer.logger.getLogBufferAndClear(),
            "INFO 'boingo - 1.0/main/base' remained the same\n")
        self.assertCurrentSource(
            self.warty, 'boingo', '1.0', 'main', 'base')

        changer.processBinaryChange('boingo-bin')
        self.assertEqual(
            changer.logger.getLogBufferAndClear(),
            "INFO 'boingo-bin-1.0/main/base/STANDARD' remained the same\n"
            "INFO 'boingo-bin-1.0/main/base/STANDARD' remained the same\n")
        self.assertCurrentBinary(
            self.warty_i386, 'boingo-bin', '1.0', 'main', 'base', 'STANDARD')
        self.assertCurrentBinary(
            self.warty_hppa, 'boingo-bin', '1.0', 'main', 'base', 'STANDARD')

        changer.processChildrenChange('boingo')
        self.assertEqual(
            changer.logger.getLogBufferAndClear(),
            "INFO 'boingo-bin-1.0/main/base/STANDARD' remained the same\n"
            "INFO 'boingo-bin-1.0/main/base/STANDARD' remained the same\n"
            "INFO 'boingo-data-0.9/main/base/STANDARD' remained the same\n"
            "INFO 'boingo-data-0.9/main/base/STANDARD' remained the same\n")
        self.assertCurrentBinary(
            self.warty_i386, 'boingo-data', '0.9', 'main', 'base', 'STANDARD')
        self.assertCurrentBinary(
            self.warty_hppa, 'boingo-data', '0.9', 'main', 'base', 'STANDARD')

    def test_overrides_with_changed_archive(self):
        """Overrides resulting in archive changes are not allowed.

        Changing the component to 'partner' will result in the archive
        changing on the publishing record.
        """
        self._setupOverridePublishingContext()

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

# Copyright 2006 Canonical Ltd.  All rights reserved.
"""ftpmaster facilities tests."""

__metaclass__ = type

from unittest import TestLoader
import shutil
import subprocess
import os
import sys

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.testing import LaunchpadZopelessLayer
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.launchpad.database.component import ComponentSelection
from canonical.launchpad.interfaces import (
    IDistributionSet, IComponentSet, ISectionSet)
from canonical.launchpad.scripts import FakeLogger
from canonical.launchpad.scripts.ftpmaster import (
    ArchiveOverrider, ArchiveOverriderError)
from canonical.lp.dbschema import (
    PackagePublishingPocket, PackagePublishingPriority)


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


class TestArchiveOverrider(LaunchpadZopelessTestCase):
    layer = LaunchpadZopelessLayer
    dbuser = config.archivepublisher.dbuser

    def setUp(self):
        """Setup the test environment and retrieve useful instances."""
        LaunchpadZopelessTestCase.setUp(self)
        self.log = LocalLogger()

        self.ubuntu = getUtility(IDistributionSet)['ubuntu']
        self.warty = self.ubuntu['warty']
        self.hoary = self.ubuntu['hoary']
        self.component_main = getUtility(IComponentSet)['main']
        self.section_base = getUtility(ISectionSet)['base']

        # Allow partner in warty and hoary.
        partner_component = getUtility(IComponentSet)['partner']
        ComponentSelection(distroseries=self.warty,
                           component=partner_component)
        ComponentSelection(distroseries=self.hoary,
                           component=partner_component)

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

    def assertBinaryPublished(self, distroarchseries, name, version,
                              component_name, section_name, priority_name):
        """Assert if the current binary publication matches the given data."""
        dasbpr = distroarchseries.getBinaryPackage(name)[version]
        pub = dasbpr.current_publishing_record
        self.assertEqual(pub.status.name, 'PUBLISHED')
        self.assertEqual(pub.component.name, component_name)
        self.assertEqual(pub.section.name, section_name)
        self.assertEqual(pub.priority.name, priority_name)

    def assertSourcePublished(self, distroseries, name, version,
                              component_name, section_name):
        """Assert if the current source publication matches the given data."""
        dsspr = distroseries.getSourcePackage(name)[version]
        pub = dsspr.current_published
        self.assertEqual(pub.status.name, 'PUBLISHED')
        self.assertEqual(pub.component.name, component_name)
        self.assertEqual(pub.section.name, section_name)

    def assertBinaryPending(self, distroarchseries, name, version,
                            component_name, section_name, priority_name):
        """Assert if the pending binary publication matches the given data."""
        dasbpr = distroarchseries.getBinaryPackage(name)[version]
        pub = dasbpr.publishing_history[0]
        self.assertEqual(pub.status.name, 'PENDING')
        self.assertEqual(pub.component.name, component_name)
        self.assertEqual(pub.section.name, section_name)
        self.assertEqual(pub.priority.name, priority_name)

    def assertSourcePending(self, distroseries, name, version,
                            component_name, section_name):
        """Assert if the pending binary publication matches the given data."""
        dsspr = distroseries.getSourcePackage(name)[version]
        pub = dsspr.publishing_history[0]
        self.assertEqual(pub.status.name, 'PENDING')
        self.assertEqual(pub.component.name, component_name)
        self.assertEqual(pub.section.name, section_name)

    def test_processSourceChange_success(self):
        """Check processSourceChange method call.

        It simply wraps changeOverride method on
        IDistroSeriesSourcePackageRelease, which is already tested in place.
        Inspect the log to verify if the correct source was picked and correct
        arguments was passed.
        """
        self.assertSourcePublished(
            self.warty, 'mozilla-firefox', '0.9', 'main', 'web')

        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='warty',
            component_name='main', section_name='base', priority_name='extra')
        changer.initialize()
        changer.processSourceChange('mozilla-firefox')
        self.assertEqual(
            self.log.read(),
            "INFO Override Component to: 'main'\n"
            "INFO Override Section to: 'base'\n"
            "INFO Override Priority to: 'EXTRA'\n"
            "INFO 'mozilla-firefox - 0.9/main/base' source overridden")

        self.assertSourcePending(
            self.warty, 'mozilla-firefox', '0.9', 'main', 'base')

    def test_processSourceChange_with_changed_archive(self):
        """Check processSourceChange method call with an archive change.

        Changing the component to 'partner' will result in the archive
        changing on the publishing record.  This is disallowed.
        """
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='warty',
            component_name='partner', section_name='base',
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
            "INFO Override Component to: 'main'\n"
            "INFO Override Section to: 'base'\n"
            "INFO Override Priority to: 'EXTRA'\n"
            "ERROR 'mozilla-firefox' source isn't published in hoary")

    def test_processSourceChange_no_change(self):
        """Source override when the source is already in the desired state.

        Nothing is done and the situation is logged.
        """
        self.assertSourcePublished(
            self.warty, 'mozilla-firefox', '0.9', 'main', 'web')

        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='warty',
            component_name='main', section_name='web',
            priority_name='extra')
        changer.initialize()
        changer.processSourceChange('mozilla-firefox')
        self.assertEqual(
            self.log.read(),
            "INFO Override Component to: 'main'\n"
            "INFO Override Section to: 'web'\n"
            "INFO Override Priority to: 'EXTRA'\n"
            "INFO 'mozilla-firefox - 0.9/main/editors' remained the same")

        # Note that there is already another PENDING publishing record
        # for mozilla-firefox in warty and it is targeted to section 'base'
        # XXX cprov 20071020: we don't treat this case very well.
        self.assertSourcePending(
            self.warty, 'mozilla-firefox', '0.9', 'main', 'editors')

    def test_processBinaryChange_success(self):
        """Check if processBinaryChange() picks the correct binary.

        It simply wraps changeOverride method on
        IDistroArchSeriesBinaryPackage, which is already tested in place.
        Inspect the log messages, check if the correct binary was picked
        and correct argument was passed.
        """
        hoary_i386 = self.hoary['i386']
        self.assertBinaryPublished(
            hoary_i386, 'pmount', '0.1-1', 'universe', 'editors', 'IMPORTANT')

        hoary_hppa = self.hoary['hppa']
        self.assertBinaryPublished(
            hoary_hppa, 'pmount', '2:1.9-1', 'main', 'base', 'EXTRA')

        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary',
            component_name='main', section_name='devel', priority_name='extra')
        changer.initialize()
        changer.processBinaryChange('pmount')
        self.assertEqual(
            self.log.read(),
            "INFO Override Component to: 'main'\n"
            "INFO Override Section to: 'devel'\n"
            "INFO Override Priority to: 'EXTRA'\n"
            "INFO 'pmount-2:1.9-1/main/base/EXTRA' binary "
                "overridden in hoary hppa\n"
            "INFO 'pmount-0.1-1/universe/editors/IMPORTANT' binary "
                "overridden in hoary i386")

        self.assertBinaryPending(
            hoary_i386, 'pmount', '0.1-1', 'main', 'devel', 'EXTRA')
        self.assertBinaryPending(
            hoary_hppa, 'pmount', '2:1.9-1', 'main', 'devel', 'EXTRA')

    def test_processBinaryChangeWithBuildInParentRelease(self):
        """Check if inherited binaries get overriden correctly.

        Modify the build records in question to emulate the situation where
        the binaries were built in the parentrelease.
        """
        hoary_i386 = self.hoary['i386']
        self.assertBinaryPublished(
            hoary_i386, 'pmount', '0.1-1', 'universe', 'editors', 'IMPORTANT')

        hoary_hppa = self.hoary['hppa']
        self.assertBinaryPublished(
            hoary_hppa, 'pmount', '2:1.9-1', 'main', 'base', 'EXTRA')

        pmount_i386 = hoary_i386.getBinaryPackage('pmount')['0.1-1']
        i386_build = removeSecurityProxy(
            pmount_i386.binarypackagerelease.build)
        i386_build.distroarchseries = self.warty['i386']

        pmount_hppa = hoary_hppa.getBinaryPackage('pmount')['2:1.9-1']
        hppa_build = removeSecurityProxy(
            pmount_hppa.binarypackagerelease.build)
        hppa_build.distroarchseries = self.warty['hppa']

        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary',
            component_name='main', section_name='devel', priority_name='extra')
        changer.initialize()
        changer.processBinaryChange('pmount')
        self.assertEqual(
            self.log.read(),
            "INFO Override Component to: 'main'\n"
            "INFO Override Section to: 'devel'\n"
            "INFO Override Priority to: 'EXTRA'\n"
            "INFO 'pmount-2:1.9-1/main/base/EXTRA' binary "
                "overridden in hoary hppa\n"
            "INFO 'pmount-0.1-1/universe/editors/IMPORTANT' binary "
                "overridden in hoary i386")

        self.assertBinaryPending(
            hoary_i386, 'pmount', '0.1-1', 'main', 'devel', 'EXTRA')
        self.assertBinaryPending(
            hoary_hppa, 'pmount', '2:1.9-1', 'main', 'devel', 'EXTRA')

    def test_processBinaryChange_with_changed_archive(self):
        """Check processBinaryChange method call with an archive change.

        Changing the component to 'partner' will result in the archive
        changing.  This is disallowed.
        """
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary',
            component_name='partner', section_name='base',
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
            "INFO Override Component to: 'main'\n"
            "INFO Override Section to: 'base'\n"
            "INFO Override Priority to: 'EXTRA'\n"
            "ERROR 'evolution' binary not found.")

    def test_processChildrenChange_success(self):
        """processChildrenChanges, modify the source and its binary children.

        It simply used the local processChangeSource on a passed name and
        processChangeBinary on each retrieved binary child.
        Inspect the log and to ensure we are passing correct arguments and
        picking the correct source.
        """
        warty_i386 = self.warty['i386']
        self.assertBinaryPublished(
            warty_i386, 'mozilla-firefox', '1.0', 'main', 'base', 'IMPORTANT')
        self.assertBinaryPublished(
            warty_i386, 'mozilla-firefox-data', '0.9', 'main', 'base', 'EXTRA')

        warty_hppa = self.warty['hppa']
        self.assertBinaryPublished(
            warty_hppa, 'mozilla-firefox', '0.9', 'main', 'base', 'EXTRA')
        self.assertBinaryPublished(
            warty_hppa, 'mozilla-firefox-data', '0.9', 'main', 'base', 'EXTRA')

        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='warty',
            component_name='main', section_name='web',
            priority_name='extra')
        changer.initialize()
        changer.processChildrenChange('mozilla-firefox')
        self.assertEqual(
            self.log.read(),
            "INFO Override Component to: 'main'\n"
            "INFO Override Section to: 'web'\n"
            "INFO Override Priority to: 'EXTRA'\n"
            "INFO 'mozilla-firefox-1.0/main/base/IMPORTANT' "
                "binary overridden in warty i386\n"
            "INFO 'mozilla-firefox-0.9/main/base/EXTRA' "
                "binary overridden in warty hppa\n"
            "INFO 'mozilla-firefox-data-0.9/main/base/EXTRA' "
                "binary overridden in warty hppa\n"
            "INFO 'mozilla-firefox-data-0.9/main/base/EXTRA' "
                "binary overridden in warty i386")

        self.assertBinaryPending(
            warty_i386, 'mozilla-firefox', '1.0', 'main', 'web', 'EXTRA')
        self.assertBinaryPending(
            warty_i386, 'mozilla-firefox-data', '0.9', 'main', 'web', 'EXTRA')
        self.assertBinaryPending(
            warty_hppa, 'mozilla-firefox', '0.9', 'main', 'web', 'EXTRA')
        self.assertBinaryPending(
            warty_hppa, 'mozilla-firefox-data', '0.9', 'main', 'web', 'EXTRA')

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
            "INFO Override Component to: 'main'\n"
            "INFO Override Section to: 'base'\n"
            "INFO Override Priority to: 'EXTRA'\n"
            "ERROR 'pmount' source isn't published in warty")

        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary',
            component_name='main', section_name='base',
            priority_name='extra')
        changer.initialize()
        changer.processChildrenChange('pmount')
        self.assertEqual(
            self.log.read(),
            "INFO Override Component to: 'main'\n"
            "INFO Override Section to: 'base'\n"
            "INFO Override Priority to: 'EXTRA'\n"
            "WARNING 'pmount' has no binaries published in hoary")


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

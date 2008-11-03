# Copyright 2006 Canonical Ltd.  All rights reserved.
"""ftpmaster facilities tests."""

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.database.component import ComponentSelection
from canonical.launchpad.interfaces import (
    IComponentSet, IDistributionSet, ISectionSet,
    PackagePublishingPocket, PackagePublishingPriority)
from canonical.launchpad.scripts import FakeLogger
from canonical.launchpad.scripts.changeoverride import (
    ChangeOverride, ArchiveOverriderError)
from canonical.launchpad.scripts.ftpmasterbase import SoyuzScriptError
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
        self.ubuntu = getUtility(IDistributionSet)['ubuntu']


    def getChanger(self, sourcename='mozilla-firefox', sourceversion=None,
                   distribution='ubuntu', suite='hoary',
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
            self.ubuntu['hoary'], changer.location.distroseries)
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

    def test_processSourceChange_success(self):
        """Check processSourceChange method call.

        It simply wraps changeOverride method on `IArchivePublisher`, which is
        already tested in place. Inspect the log to verify if the correct
        source was picked and correct arguments was passed.
        """
        self.assertCurrentSource(
            self.ubuntu.getSeries('warty'), 'mozilla-firefox', '0.9',
            'main', 'web')

        changer = self.getChanger(
            suite="warty", component="main", section="base", priority="extra")
        changer.processSourceChange('mozilla-firefox')
        self.assertEqual(
            changer.logger.read(),
            "INFO Override Component to: 'main'\n"
            "INFO Override Section to: 'base'\n"
            "INFO Override Priority to: 'EXTRA'\n"
            "INFO 'mozilla-firefox - 0.9/main/web' source overridden")

        self.assertCurrentSource(
            self.ubuntu.getSeries('warty'), 'mozilla-firefox', '0.9',
            'main', 'base')

    def test_processBinaryChange_success(self):
        """Check if processBinaryChange() picks the correct binary.

        It simply wraps changeOverride method on `IArchivePublisher`, which
        is already tested in place. Inspect the log messages, check if the
        correct binary was picked and correct argument was passed.
        """
        hoary = self.ubuntu.getSeries('hoary')
        hoary_i386 = hoary['i386']
        self.assertCurrentBinary(
            hoary_i386, 'pmount', '0.1-1', 'universe', 'editors', 'IMPORTANT')

        hoary_hppa = hoary['hppa']
        self.assertCurrentBinary(
            hoary_hppa, 'pmount', '2:1.9-1', 'main', 'base', 'EXTRA')

        changer = self.getChanger(
            component="main", section="devel", priority="extra")
        changer.processBinaryChange('pmount')
        self.assertEqual(
            changer.logger.read(),
            "INFO Override Component to: 'main'\n"
            "INFO Override Section to: 'devel'\n"
            "INFO Override Priority to: 'EXTRA'\n"
            "INFO 'pmount-2:1.9-1/main/base/EXTRA' binary "
                "overridden in hoary/hppa\n"
            "INFO 'pmount-0.1-1/universe/editors/IMPORTANT' binary "
                "overridden in hoary/i386")

        self.assertCurrentBinary(
            hoary_i386, 'pmount', '0.1-1', 'main', 'devel', 'EXTRA')
        self.assertCurrentBinary(
            hoary_hppa, 'pmount', '2:1.9-1', 'main', 'devel', 'EXTRA')

    def test_processChildrenChange_success(self):
        """processChildrenChanges, modify the source and its binary children.

        It simply used the local processChangeSource on a passed name and
        processChangeBinary on each retrieved binary child.
        Inspect the log and to ensure we are passing correct arguments and
        picking the correct source.
        """
        warty = self.ubuntu.getSeries('warty')
        warty_i386 = warty['i386']
        self.assertCurrentBinary(
            warty_i386, 'mozilla-firefox', '1.0', 'main', 'base', 'IMPORTANT')
        self.assertCurrentBinary(
            warty_i386, 'mozilla-firefox-data', '0.9', 'main', 'base',
            'EXTRA')

        warty_hppa = warty['hppa']
        self.assertCurrentBinary(
            warty_hppa, 'mozilla-firefox', '0.9', 'main', 'base', 'EXTRA')
        self.assertCurrentBinary(
            warty_hppa, 'mozilla-firefox-data', '0.9', 'main', 'base',
            'EXTRA')

        changer = self.getChanger(
            suite="warty", component="main", section="web", priority="extra")
        changer.processChildrenChange('mozilla-firefox')
        self.assertEqual(
            changer.logger.read(),
            "INFO Override Component to: 'main'\n"
            "INFO Override Section to: 'web'\n"
            "INFO Override Priority to: 'EXTRA'\n"
            "INFO 'mozilla-firefox-0.9/main/base/EXTRA' "
                "binary overridden in warty/hppa\n"
            "INFO 'mozilla-firefox-1.0/main/base/IMPORTANT' "
                "binary overridden in warty/i386\n"
            "INFO 'mozilla-firefox-data-0.9/main/base/EXTRA' "
                "binary overridden in warty/hppa\n"
            "INFO 'mozilla-firefox-data-0.9/main/base/EXTRA' "
                "binary overridden in warty/i386")

        self.assertCurrentBinary(
            warty_i386, 'mozilla-firefox', '1.0', 'main', 'web', 'EXTRA')
        self.assertCurrentBinary(
            warty_i386, 'mozilla-firefox-data', '0.9', 'main', 'web', 'EXTRA')
        self.assertCurrentBinary(
            warty_hppa, 'mozilla-firefox', '0.9', 'main', 'web', 'EXTRA')
        self.assertCurrentBinary(
            warty_hppa, 'mozilla-firefox-data', '0.9', 'main', 'web', 'EXTRA')

    def test_processSourceChange_no_change(self):
        """Source override when the source is already in the desired state.

        Nothing is done and the situation is logged.
        """
        self.assertCurrentSource(
            self.ubuntu.getSeries('warty'), 'mozilla-firefox', '0.9',
            'main', 'web')

        changer = self.getChanger(
            suite="warty", component="main", section="web", priority="extra")
        changer.processSourceChange('mozilla-firefox')
        self.assertEqual(
            changer.logger.read(),
            "INFO Override Component to: 'main'\n"
            "INFO Override Section to: 'web'\n"
            "INFO Override Priority to: 'EXTRA'\n"
            "INFO 'mozilla-firefox - 0.9/main/web' remained the same")

        self.assertCurrentSource(
            self.ubuntu.getSeries('warty'), 'mozilla-firefox', '0.9',
            'main', 'web')

    def test_overrides_with_changed_archive(self):
        """Check processSourceChange method call with an archive change.

        Changing the component to 'partner' will result in the archive
        changing on the publishing record.  This is disallowed.
        """
        changer = self.getChanger(
            suite="warty", component="partner", section="base",
            priority="extra")
        self.assertRaises(
            ArchiveOverriderError, changer.processSourceChange,
            'mozilla-firefox')

        changer = self.getChanger(
            component="partner", section="base", priority="extra")
        self.assertRaises(
            ArchiveOverriderError, changer.processBinaryChange, 'pmount')

        changer = self.getChanger(
            suite="warty", component="partner", section="web",
            priority="extra")
        self.assertRaises(
            ArchiveOverriderError, changer.processChildrenChange,
            'mozilla-firefox')

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

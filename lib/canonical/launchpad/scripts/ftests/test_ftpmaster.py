# Copyright 2006 Canonical Ltd.  All rights reserved.
"""ftpmaster facilities tests."""

__metaclass__ = type

from StringIO import StringIO
from unittest import TestCase, TestLoader

from zope.component import getUtility

from canonical.functional import ZopelessLayer
from canonical.launchpad.ftests.harness import LaunchpadTestSetup
from canonical.launchpad.interfaces import (
    IDistributionSet, IComponentSet, ISectionSet)
from canonical.launchpad.scripts.ftpmaster import (
    ArchiveOverrider, ArchiveOverriderError)
from canonical.lp import initZopeless
from canonical.lp.dbschema import (
    PackagePublishingPocket, PackagePublishingPriority)

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


class TestArchiveOverrider(TestCase):
    layer = ZopelessLayer

    def setUp(self):
        LaunchpadTestSetup().setUp()
        self.ztm = initZopeless(dbuser='lucille')
        self.log = MockLogger()

    def tearDown(self):
        LaunchpadTestSetup().tearDown()
        self.ztm.uninstall()

    def test_initialize_success(self):
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary',
            component_name='main', section_name='base', priority_name='extra')
        changer.initialize()

        ubuntu = getUtility(IDistributionSet)['ubuntu']
        hoary = ubuntu['hoary']
        component_main = getUtility(IComponentSet)['main']
        section_base = getUtility(ISectionSet)['base']

        self.assertEqual(ubuntu, changer.distro)
        self.assertEqual(hoary, changer.distrorelease)
        self.assertEqual(PackagePublishingPocket.RELEASE, changer.pocket)
        self.assertEqual(component_main, changer.component)
        self.assertEqual(section_base, changer.section)
        self.assertEqual(PackagePublishingPriority.EXTRA, changer.priority)

        self.log.read()

    def test_initialize_broken_distro(self):
        changer = ArchiveOverrider(
            self.log, distro_name='foo', suite='hoary',
            component_name='main', section_name='base', priority_name='extra')
        self.assertRaises(
            ArchiveOverriderError, changer.initialize)
        self.log.read()

    def test_initialize_broken_suite(self):
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='bar',
            component_name='main', section_name='base', priority_name='extra')
        self.assertRaises(
            ArchiveOverriderError, changer.initialize)
        self.log.read()

    def test_initialize_full_suite(self):
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
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary',
            component_name='baz', section_name='base', priority_name='extra')
        self.assertRaises(
            ArchiveOverriderError, changer.initialize)
        self.log.read()

    def test_initialize_broken_section(self):
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary',
            component_name='main', section_name='bozo', priority_name='extra')
        self.assertRaises(
            ArchiveOverriderError, changer.initialize)
        self.log.read()

    def test_initialize_broken_priority(self):
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='hoary',
            component_name='main', section_name='base', priority_name='bingo')
        self.assertRaises(
            ArchiveOverriderError, changer.initialize)
        self.log.read()

    def test_processSourceChange_success(self):
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
            "INFO: 'mozilla-firefox/main/web' source overriden")

    def test_processSourceChange_failed(self):
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
            "ERROR: u'Source package mozilla-firefox not published in hoary'")

    def test_processBinaryChange_success(self):
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
            "INFO: 'pmount/universe/editors/IMPORTANT' "
            "binary overriden in hoary/i386")

    def test_processBinaryChange_failed(self):
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
            "ERROR: 'evolution' binary isn't published in warty/i386")

    def test_processChildrenChange_success(self):
        changer = ArchiveOverrider(
            self.log, distro_name='ubuntu', suite='warty',
            component_name='main', section_name='base',
            priority_name='important')
        changer.initialize()
        changer.processChildrenChange('mozilla-firefox')
        self.assertEqual(
            self.log.read(),
            "INFO: Override Component to: 'main'\n"
            "INFO: Override Section to: 'base'\n"
            "INFO: Override Priority to: 'IMPORTANT'\n"
            "INFO: 'mozilla-firefox/main/base/EXTRA' "
            "binary overriden in warty/i386")

    def test_processChildrenChange_failed(self):
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

def test_suite():
    return TestLoader().loadTestsFromName(__name__)

# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Test the SoyuzScript base class.

We check that the base source and binary lookup methods are working
properly.
"""

import unittest

from canonical.launchpad.ftests.harness import LaunchpadZopelessTestCase
from canonical.launchpad.scripts import FakeLogger
from canonical.launchpad.scripts.ftpmasterbase import (
    SoyuzScriptError, SoyuzScript)


class TestSoyuzScript(LaunchpadZopelessTestCase):
    """Test the SoyuzScript class."""

    def getNakedSoyuz(self, version=None, component=None, arch=None,
                      suite=None, distribution_name='ubuntu'):
        """Return a SoyuzScript instance.

        Do not call SoyuzScript.setupLocation().
        Allow tests to use a set of default options and pass an
        inactive logger to SoyuzScript.
        """
        test_args=['-d', distribution_name, '-y' ]

        if suite is not None:
            test_args.extend(['-s', suite])

        if version is not None:
            test_args.extend(['-e', version])

        if arch is not None:
            test_args.extend(['-a', arch])

        if component is not None:
            test_args.extend(['-c', component])

        soyuz = SoyuzScript(name='soyuz-script', test_args=test_args)
        # Swallowing all log messages.
        soyuz.logger = FakeLogger()
        def message(self, prefix, *stuff, **kw):
            pass
        soyuz.logger.message = message
        return soyuz

    def getSoyuz(self, *args, **kwargs):
        """Return an initialized SoyuzScript instance."""
        soyuz = self.getNakedSoyuz(*args, **kwargs)
        soyuz.setupLocation()
        return soyuz

    def testSetupLocation(self):
        """Check if `SoyuzScript` handles `PackageLocation` properly.

        SoyuzScriptError is raised on not-found or broken locations.
        """
        soyuz = self.getSoyuz()

        self.assertEqual(soyuz.location.distribution.name, 'ubuntu')
        self.assertEqual(soyuz.location.distroseries.name, 'hoary')
        self.assertEqual(soyuz.location.pocket.name, 'RELEASE')

        soyuz = self.getNakedSoyuz(distribution_name='beeblebrox')
        self.assertRaises(SoyuzScriptError, soyuz.setupLocation)

        soyuz = self.getNakedSoyuz(suite='beeblebrox')
        self.assertRaises(SoyuzScriptError, soyuz.setupLocation)

    def testFindSource(self):
        """The findSource method of SoyuzScript finds pmount in the
        default component, main, but not in other components or with a
        non-existent version, etc.
        """
        soyuz = self.getSoyuz()
        src = soyuz.findSource('pmount')
        self.assertEqual(
            src.displayname, 'pmount 0.1-2 in hoary')

        soyuz = self.getSoyuz(suite='hoary', component='main')
        src = soyuz.findSource('pmount')
        self.assertEqual(
            src.displayname, 'pmount 0.1-2 in hoary')

        soyuz = self.getSoyuz()
        self.assertRaises(SoyuzScriptError, soyuz.findSource, 'marvin')

        soyuz = self.getSoyuz(version='666')
        self.assertRaises(SoyuzScriptError, soyuz.findSource, 'pmount')

        soyuz = self.getSoyuz(component='multiverse')
        self.assertRaises(SoyuzScriptError, soyuz.findSource, 'pmount')

        soyuz = self.getSoyuz(suite='hoary-security')
        self.assertRaises(SoyuzScriptError, soyuz.findSource, 'pmount')

    def testFindBinaries(self):
        """The findBinary method of SoyuzScript finds mozilla-firefox in the
        default component, main, but not in other components or with a
        non-existent version, etc.
        """
        soyuz = self.getSoyuz()

        binaries = soyuz.findBinaries('pmount')
        self.assertEqual(len(binaries), 2)
        binary_names = set([b.binarypackagerelease.name for b in binaries])
        self.assertEqual(list(binary_names), ['pmount'])

        self.assertRaises(SoyuzScriptError, soyuz.findBinaries, 'marvin')

        soyuz = self.getSoyuz(version='666')
        self.assertRaises(
            SoyuzScriptError, soyuz.findBinaries, 'pmount')

        soyuz = self.getSoyuz(component='multiverse')
        self.assertRaises(
            SoyuzScriptError, soyuz.findBinaries, 'pmount')

        soyuz = self.getSoyuz(suite='warty-security')
        self.assertRaises(
            SoyuzScriptError, soyuz.findBinaries, 'pmount')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

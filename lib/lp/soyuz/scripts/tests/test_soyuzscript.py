# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the SoyuzScript base class.

We check that the base source and binary lookup methods are working
properly.
"""

import unittest

from zope.component import getUtility

from lp.registry.interfaces.person import IPersonSet
from lp.services.log.logger import BufferLogger
from lp.soyuz.scripts.ftpmasterbase import (
    SoyuzScript,
    SoyuzScriptError,
    )
from lp.testing.layers import LaunchpadZopelessLayer


class TestSoyuzScript(unittest.TestCase):
    """Test the SoyuzScript class."""

    layer = LaunchpadZopelessLayer

    def getSoyuz(self, version=None, component=None, arch=None,
                 suite=None, distribution_name='ubuntu',
                 ppa=None, partner=False, ppa_name='ppa'):
        """Return a SoyuzScript instance.

        Allow tests to use a set of default options and pass an
        inactive logger to SoyuzScript.
        """
        test_args = ['-d', distribution_name, '-y']

        if suite is not None:
            test_args.extend(['-s', suite])

        if version is not None:
            test_args.extend(['-e', version])

        if arch is not None:
            test_args.extend(['-a', arch])

        if component is not None:
            test_args.extend(['-c', component])

        if ppa is not None:
            test_args.extend(['-p', ppa])
            test_args.extend(['--ppa-name', ppa_name])

        if partner:
            test_args.append('-j')

        soyuz = SoyuzScript(name='soyuz-script', test_args=test_args)
        # Store output messages, for future checks.
        soyuz.logger = BufferLogger()
        soyuz.setupLocation()
        return soyuz

    def testFindLatestPublishedSourceInPRIMARY(self):
        """Source lookup in PRIMARY archive."""
        soyuz = self.getSoyuz()
        src = soyuz.findLatestPublishedSource('pmount')
        self.assertEqual(src.displayname, 'pmount 0.1-2 in hoary')

        self.assertRaises(
            SoyuzScriptError, soyuz.findLatestPublishedSource, 'marvin')

        soyuz = self.getSoyuz(suite='hoary-security')
        self.assertRaises(
            SoyuzScriptError, soyuz.findLatestPublishedSource, 'pmount')

    def testFindLatestPublishedSourceInPARTNER(self):
        """Source lookup in PARTNER archive."""
        soyuz = self.getSoyuz(suite='breezy-autotest', partner=True)
        src = soyuz.findLatestPublishedSource('commercialpackage')
        self.assertEqual(
            src.displayname, 'commercialpackage 1.0-1 in breezy-autotest')

        self.assertRaises(
            SoyuzScriptError, soyuz.findLatestPublishedSource, 'marvin')

        soyuz = self.getSoyuz(suite='warty', partner=True)
        self.assertRaises(
            SoyuzScriptError, soyuz.findLatestPublishedSource,
            'commercialpackage')

    def testFindLatestPublishedSourceInPPA(self):
        """Source lookup in PPAs."""
        soyuz = self.getSoyuz(ppa='cprov', suite='warty')
        src = soyuz.findLatestPublishedSource('pmount')
        self.assertEqual(src.displayname, 'pmount 0.1-1 in warty')

        self.assertRaises(
            SoyuzScriptError, soyuz.findLatestPublishedSource, 'marvin')

        soyuz = self.getSoyuz(ppa='cprov', suite='warty-security')
        self.assertRaises(
            SoyuzScriptError, soyuz.findLatestPublishedSource, 'pmount')

        # Bug 159151 occurred because we were printing unicode characters
        # to an ascii codec in the exception, which originated in the PPA
        # owner's name.  Let's munge cprov's name to be unicode and ensure
        # we still get the right exception raised (a UnicodeError is raised
        # if the bug is present).
        cprov = getUtility(IPersonSet).getByName('cprov')
        cprov.displayname = u'\xe7\xe3o'
        self.assertRaises(
            SoyuzScriptError, soyuz.findLatestPublishedSource, 'pmount')

    def testFindLatestPublishedSourceAndCheckComponent(self):
        """Before returning the source publication component is checked.

        Despite of existing the found publication should match the given
        component (if given) otherwise an error is raised.
        """
        soyuz = self.getSoyuz(suite='hoary', component='main')
        src = soyuz.findLatestPublishedSource('pmount')
        self.assertEqual(src.displayname, 'pmount 0.1-2 in hoary')

        soyuz = self.getSoyuz(component='multiverse')
        self.assertRaises(
            SoyuzScriptError, soyuz.findLatestPublishedSource, 'pmount')

    def testFindLatestPublishedSourceWithSpecificVersion(self):
        """Source lookups for specific version."""
        soyuz = self.getSoyuz(version='0.1-2')
        src = soyuz.findLatestPublishedSource('pmount')
        self.assertEqual(src.displayname, 'pmount 0.1-2 in hoary')

        soyuz = self.getSoyuz(version='666')
        self.assertRaises(
            SoyuzScriptError, soyuz.findLatestPublishedSource, 'pmount')

    def testFinishProcedure(self):
        """Make sure finishProcedure returns the correct boolean."""
        soyuz = self.getSoyuz()
        soyuz.txn = LaunchpadZopelessLayer.txn
        soyuz.options.confirm_all = True
        self.assertTrue(soyuz.finishProcedure())
        # XXX Julian 2007-11-29 bug=172869:
        # Setting confirm_all to False is pretty untestable because it
        # asks the user for confirmation via raw_input.
        soyuz.options.dryrun = True
        self.assertFalse(soyuz.finishProcedure())

# Copyright 2006 Canonical Ltd.  All rights reserved.
"""queue tool base class tests."""

__metaclass__ = type

from unittest import TestCase, TestLoader

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces import IDistributionSet
from canonical.launchpad.scripts.queue import (
    CommandRunner, CommandRunnerError, name_queue_map)
from canonical.lp.dbschema import PackagePublishingStatus
from canonical.testing import LaunchpadZopelessLayer


test_output = []

def test_display(text):
    """Store output from queue tool for inspection."""
    test_output.append(text)


class TestQueueTool(TestCase):
    layer = LaunchpadZopelessLayer
    dbuser = config.uploadqueue.dbuser

    def setup_runner(self, queue_name='new', distribution_name='ubuntu',
                     distrorelease_name='breezy-autotest',
                     announcelist=None, no_mail=True, quiet=True):
        """Helper method to initialize a queue command runner.

        Return a CommandRunner instance.
        """
        queue = name_queue_map[queue_name]
        return CommandRunner(
            queue, distribution_name, distrorelease_name,
            announcelist, no_mail, display=test_display)

    def testBrokenAction(self):
        """Check if an unknown action raises CommandRunnerError."""
        args = 'foo'
        runner = self.setup_runner()
        self.assertRaises(
            CommandRunnerError, runner.execute, args.split())

    def testInfoAction(self):
        """Check INFO queue action without arguments present all items."""
        args = 'info'
        runner = self.setup_runner()
        runner.execute(args.split())
        self.assertEqual(6, runner.queue_action.size)
        self.assertEqual(6, runner.queue_action.items_size)

    def testInfoActionByID(self):
        """Check INFO queue action filtering by ID"""
        args = 'info 1'
        runner = self.setup_runner()
        runner.execute(args.split())
        self.assertEqual(6, runner.queue_action.size)
        self.assertEqual(1, runner.queue_action.items_size)
        self.assertEqual(
            'mozilla-firefox', runner.queue_action.items[0].displayname)

    def testInfoActionByName(self):
        """Check INFO queue action filtering by name"""
        args = 'info pmount'
        runner = self.setup_runner()
        runner.execute(args.split())
        self.assertEqual(6, runner.queue_action.size)
        self.assertEqual(1, runner.queue_action.items_size)
        self.assertEqual('pmount', runner.queue_action.items[0].displayname)


    def testFix59291(self):
        """Check if REMOVED published record does not affect file NEWness.

        We only mark a file as *known* if there is a PUBLISHED record with
        the same name, other states like SUPERSEDED or REMOVED doesn't count.

        This is the case of 'pmount_0.1-1' in ubuntu/breezy-autotest/i386,
        there is a REMOVED publishing record for it as you can see in the
        first part of the test.

        Following we can see the correct presentation of the new flag ('N').
        """
        # inspect publishing history in sampledata for the suspicious binary
        # ensure is has a single entry and it is merked as REMOVED.
        ubuntu = getUtility(IDistributionSet)['ubuntu']
        bat_i386 = ubuntu['breezy-autotest']['i386']
        moz_publishing = bat_i386.getBinaryPackage('pmount').releases

        self.assertEqual(1, len(moz_publishing))
        self.assertEqual(PackagePublishingStatus.REMOVED,
                         moz_publishing[0].status)

        # invoke queue tool filtering by name
        args = 'info pmount'
        runner = self.setup_runner()
        runner.execute(args.split())
        # ensure we retrived a single item
        self.assertEqual(1, runner.queue_action.items_size)
        # and it is what we expect
        self.assertEqual('pmount', runner.queue_action.items[0].displayname)
        self.assertEqual(moz_publishing[0].binarypackagerelease.build,
                         runner.queue_action.items[0].builds[0].build)
        # inspect output, not the present 'N' flag
        self.assertTrue(
            '| N pmount/0.1-1/i386' in '\n'.join(test_output))



def test_suite():
    return TestLoader().loadTestsFromName(__name__)

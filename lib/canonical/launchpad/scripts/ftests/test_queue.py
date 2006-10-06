# Copyright 2006 Canonical Ltd.  All rights reserved.
"""queue tool base class tests."""

__metaclass__ = type

from unittest import TestCase, TestLoader

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces import (
    IDistributionSet, IDistroReleaseQueueSet)
from canonical.launchpad.mail import stub
from canonical.launchpad.scripts.queue import (
    CommandRunner, CommandRunnerError, name_queue_map)
from canonical.librarian.ftests.harness import (
    fillLibrarianFile, removeLibrarianFile)
from canonical.lp.dbschema import (
    PackagePublishingStatus, PackagePublishingPocket,
    DistroReleaseQueueStatus, DistributionReleaseStatus)
from canonical.testing import LaunchpadZopelessLayer


class TestQueueTool(TestCase):
    layer = LaunchpadZopelessLayer
    dbuser = config.uploadqueue.dbuser

    def _test_display(self, text):
        """Store output from queue tool for inspection."""
        self.test_output.append(text)

    def execute_command(self, argument, queue_name='new', no_mail=True,
                        distribution_name='ubuntu',announcelist=None,
                        suite_name='breezy-autotest', quiet=True):
        """Helper method to execute a queue command.

        Initialise output buffer and execute a command according
        given argument.

        Return the used QueueAction instance.
        """
        self.test_output = []

        queue = name_queue_map[queue_name]

        runner = CommandRunner(
            queue, distribution_name, suite_name, announcelist, no_mail,
            display=self._test_display)

        return runner.execute(argument.split())

    def testBrokenAction(self):
        """Check if an unknown action raises CommandRunnerError."""
        self.assertRaises(
            CommandRunnerError, self.execute_command, 'foo')

    def testInfoAction(self):
        """Check INFO queue action without arguments present all items."""
        queue_action = self.execute_command('info')
        # check if the considered queue size matches the existent number
        # of records in sampledata
        bat = getUtility(IDistributionSet)['ubuntu']['breezy-autotest']
        queue_size = getUtility(IDistroReleaseQueueSet).count(
            status=DistroReleaseQueueStatus.NEW,
            distrorelease=bat, pocket= PackagePublishingPocket.RELEASE)
        self.assertEqual(queue_size, queue_action.size)
        # check if none of them was filtered, since not filter term
        # was passed.
        self.assertEqual(queue_size, queue_action.items_size)

    def testInfoActionByID(self):
        """Check INFO queue action filtering by ID"""
        queue_action = self.execute_command('info 1')
        # check if only one item was retrieved
        self.assertEqual(1, queue_action.items_size)

        displaynames = [item.displayname for item in queue_action.items]
        self.assertEqual(['mozilla-firefox'], displaynames)

    def testInfoActionByName(self):
        """Check INFO queue action filtering by name"""
        queue_action = self.execute_command('info pmount')
        # check if only one item was retrieved as expected in the current
        # sampledata
        self.assertEqual(1, queue_action.items_size)

        displaynames = [item.displayname for item in queue_action.items]
        self.assertEqual(['pmount'], displaynames)

    def testRemovedPublishRecordDoesNotAffectQueueNewNess(self):
        """Check if REMOVED published record does not affect file NEWness.

        We only mark a file as *known* if there is a PUBLISHED record with
        the same name, other states like SUPERSEDED or REMOVED doesn't count.

        This is the case of 'pmount_0.1-1' in ubuntu/breezy-autotest/i386,
        there is a REMOVED publishing record for it as you can see in the
        first part of the test.

        Following we can see the correct presentation of the new flag ('N').
        Bug #59291
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
        queue_action = self.execute_command('info pmount')

        # ensure we retrived a single item
        self.assertEqual(1, queue_action.items_size)

        # and it is what we expect
        self.assertEqual('pmount', queue_action.items[0].displayname)
        self.assertEqual(moz_publishing[0].binarypackagerelease.build,
                         queue_action.items[0].builds[0].build)
        # inspect output, note the presence of 'N' flag
        self.assertTrue(
            '| N pmount/0.1-1/i386' in '\n'.join(self.test_output))

    def testQueueSupportForSuiteNames(self):
        """Queue tool supports suite names properly.

        No UNAPROVED items are present for pocket RELEASE), but there is
        one for pocket UPDATES in breezy-autotest.
        Bug #59280
        """
        queue_action = self.execute_command(
            'info', queue_name='unapproved',
            suite_name='breezy-autotest')

        self.assertEqual(0, queue_action.items_size)
        self.assertEqual(PackagePublishingPocket.RELEASE, queue_action.pocket)

        queue_action = self.execute_command(
            'info', queue_name='unapproved',
            suite_name='breezy-autotest-updates')

        self.assertEqual(1, queue_action.items_size)
        self.assertEqual(PackagePublishingPocket.UPDATES, queue_action.pocket)

    def testQueueDoesNotAnnounceBackports(self):
        """Check if BACKPORTS acceptance are not announced publicly.

        Queue tool normally announce acceptance in the specified changeslist
        for the distrorelease in question, however BACKPORTS announce doesn't
        fit very well in that list, they cause unwanted noise.

        Further details in bug #59443
        """
        # make breezy-autotest CURRENT in order to accept upload
        # to BACKPORTS
        breezy_autotest = getUtility(
            IDistributionSet)['ubuntu']['breezy-autotest']
        breezy_autotest.releasestatus = DistributionReleaseStatus.CURRENT

        # ensure breezy-autotest is set
        self.assertEqual(
            u'autotest_changes@ubutu.com', breezy_autotest.changeslist)

        # create contents for the respective changesfile in librarian.
        fillLibrarianFile(1)

        # accept the sampledata item
        queue_action = self.execute_command(
            'accept', queue_name='unapproved',
            suite_name='breezy-autotest-backports', no_mail=False)

        # only one item considered
        self.assertEqual(1, queue_action.items_size)

        # One email was sent
        self.assertEqual(1, len(stub.test_emails))

        # sent to the default recipient only, not the breezy-autotest
        # announcelist.
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        self.assertEqual([queue_action.default_recipient], to_addrs)

        removeLibrarianFile(1)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

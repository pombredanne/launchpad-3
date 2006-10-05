# Copyright 2006 Canonical Ltd.  All rights reserved.
"""queue tool base class tests."""

__metaclass__ = type

import os
import shutil
import tempfile
from unittest import TestCase, TestLoader

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces import (
    IDistributionSet, IDistroReleaseQueueSet)
from canonical.launchpad.scripts.queue import (
    CommandRunner, CommandRunnerError, name_queue_map)
from canonical.librarian.ftests.harness import (
    fillLibrarianFile, removeLibrarianFile)
from canonical.lp.dbschema import (
    PackagePublishingStatus, PackagePublishingPocket,
    DistroReleaseQueueStatus)
from canonical.testing import LaunchpadZopelessLayer


class TestQueueBase:
    """Base methods for queue tool test classes."""

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


class TestQueueTool(TestQueueBase, TestCase):
    layer = LaunchpadZopelessLayer
    dbuser = config.uploadqueue.dbuser

    def setUp(self):
        """Create contents in disk for librarian sampledata."""
        fillLibrarianFile(1)

    def tearDown(self):
        """Remove test contents from disk."""
        removeLibrarianFile(1)

    def testBrokenAction(self):
        """Check if an unknown action raises CommandRunnerError."""
        self.assertRaises(
            CommandRunnerError, self.execute_command, 'foo')

    def testHelpAction(self):
        """Check if help is working properly.

        Without arguments 'help' should return the docstring summary of
        all available actions.

        Optionally we can pass arguments corresponding to the specific
        actions we want to see the help, not available actions will be
        reported.
        """
        queue_action = self.execute_command('help')
        self.assertEqual(
            ['Running: "help"',
             '\tinfo : Present the Queue item including its contents. ',
             '\taccept : Accept the contents of a queue item. ',
             '\treport : Present a report about the size of available queues ',
             '\treject : Reject the contents of a queue item. ',
             '\toverride : Override information in a queue item content. ',
             '\tfetch : Fetch the contents of a queue item. '],
            self.test_output)

        queue_action = self.execute_command('help fetch')
        self.assertEqual(
            ['Running: "help fetch"',
             '\tfetch : Fetch the contents of a queue item. '],
            self.test_output)

        queue_action = self.execute_command('help foo')
        self.assertEqual(
            ['Running: "help foo"',
             'Not available action(s): foo'],
            self.test_output)

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

        Two UNAPPROVED items are present for pocket RELEASE and only
        one for pocket UPDATES in breezy-autotest.
        Bug #59280
        """
        queue_action = self.execute_command(
            'info', queue_name='unapproved',
            suite_name='breezy-autotest')

        self.assertEqual(2, queue_action.items_size)
        self.assertEqual(PackagePublishingPocket.RELEASE, queue_action.pocket)

        queue_action = self.execute_command(
            'info', queue_name='unapproved',
            suite_name='breezy-autotest-updates')

        self.assertEqual(1, queue_action.items_size)
        self.assertEqual(PackagePublishingPocket.UPDATES, queue_action.pocket)

    def assertQueueLength(self, expected_length, distro_release, status, name):
        self.assertEqual(
            expected_length,
            distro_release.getQueueItems(status=status, name=name).count())

    def testAcceptanceWorkflowForDuplications(self):
        """Check how queue tool behaves dealing with duplicated entries.

        Sampledata provides a duplication of cnews_1.0 in breezy-autotest
        UNAPPROVED queue.

        1 Failed to accept both, only the oldest get accepted
        2 Failed to re-accept the remaining item
        3 Failed to re-accept the remaing item even when former is DONE
        4 Successfully rejection of the remaining item
        """
        breezy_autotest = getUtility(
            IDistributionSet)['ubuntu']['breezy-autotest']

        # 'cnews' upload duplication in UNAPPROVED
        self.assertQueueLength(
            2, breezy_autotest, DistroReleaseQueueStatus.UNAPPROVED, "cnews")

        # try to accept both
        queue_action = self.execute_command(
            'accept cnews', queue_name='unapproved',
            suite_name='breezy-autotest')

        # the first is in accepted.
        self.assertQueueLength(
            1, breezy_autotest, DistroReleaseQueueStatus.ACCEPTED, "cnews")

        # the last can't be accepted and remains in UNAPPROVED
        self.assertTrue(
            ('** cnews could not be accepted due This '
             'sourcepackagerelease is already accepted in breezy-autotest.')
            in self.test_output)
        self.assertQueueLength(
            1, breezy_autotest, DistroReleaseQueueStatus.UNAPPROVED, "cnews")

        # try to accept the remaining item in UNAPPROVED.
        queue_action = self.execute_command(
            'accept cnews', queue_name='unapproved',
            suite_name='breezy-autotest')
        self.assertTrue(
            ('** cnews could not be accepted due This '
             'sourcepackagerelease is already accepted in breezy-autotest.')
            in self.test_output)
        self.assertQueueLength(
            1, breezy_autotest, DistroReleaseQueueStatus.UNAPPROVED, "cnews")

        # simulate a publication of the accepted item, now it is in DONE
        accepted_item = breezy_autotest.getQueueItems(
            status=DistroReleaseQueueStatus.ACCEPTED, name="cnews")[0]

        accepted_item.setDone()
        accepted_item.syncUpdate()
        self.assertQueueLength(
            1, breezy_autotest, DistroReleaseQueueStatus.DONE, "cnews")

        # try to accept the remaining item in UNAPPROVED with the
        # duplication already in DONE
        queue_action = self.execute_command(
            'accept cnews', queue_name='unapproved',
            suite_name='breezy-autotest')
        # it failed and te item remains in UNAPPROVED
        self.assertTrue(
            ('** cnews could not be accepted due This '
             'sourcepackagerelease is already accepted in breezy-autotest.')
            in self.test_output)
        self.assertQueueLength(
            1, breezy_autotest, DistroReleaseQueueStatus.UNAPPROVED, "cnews")

        # The only possible destiny for the remaining item it REJECT
        queue_action = self.execute_command(
            'reject cnews', queue_name='unapproved',
            suite_name='breezy-autotest')
        self.assertQueueLength(
            0, breezy_autotest, DistroReleaseQueueStatus.UNAPPROVED, "cnews")
        self.assertQueueLength(
            1, breezy_autotest, DistroReleaseQueueStatus.REJECTED, "cnews")


class TestQueueToolInJail(TestQueueBase, TestCase):
    layer = LaunchpadZopelessLayer
    dbuser = config.uploadqueue.dbuser

    def setUp(self):
        """Create contents in disk for librarian sampledata.

        Setup and chdir into a temp directory, a jail, where we can
        control de file creation properly
        """
        fillLibrarianFile(1)
        fillLibrarianFile(52)
        self._home = os.path.abspath('')
        self._jail = tempfile.mkdtemp()
        os.chdir(self._jail)

    def tearDown(self):
        """Remove test contents from disk.

        chdir back to the previous path (home) and remove the temp
        directory used as jail.
        """
        removeLibrarianFile(1)
        removeLibrarianFile(52)
        os.chdir(self._home)
        shutil.rmtree(self._jail)

    def _listfiles(self):
        """Return a list of files present in jail."""
        return os.listdir(self._jail)

    def testFetchActionByIDDoNotOverwriteFilesystem(self):
        """Check if queue fetch action doesn't overwrite files.

        Since we allow existence of duplications in NEW and UNAPPROVED
        queues, we are able to fetch files from queue items and they'd
        get overwritten causing obscure problems.

        Instead of overwrite a file in the working directory queue will
        fail, raising a CommandRunnerError.
        """
        queue_action = self.execute_command('fetch 1')
        self.assertEqual(
            ['mozilla-firefox_0.9_i386.changes'], self._listfiles())

        # fetch will raise and not overwrite the file in disk
        self.assertRaises(
            CommandRunnerError, self.execute_command, 'fetch 1')

    def testFetchActionByNameDoNotOverwriteFilesystem(self):
        """Same as testFetchActionByIDDoNotOverwriteFilesystem

        The sampledata provides duplicated 'cnews' entries, filesystem
        conflict will happen inside the same batch,

        Queue will fetch the oldest and raise.
        """
        self.assertRaises(
            CommandRunnerError, self.execute_command, 'fetch cnews',
            queue_name='unapproved', suite_name='breezy-autotest')

        self.assertEqual(['netapplet-1.0.0.tar.gz'], self._listfiles())


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

# Copyright 2006 Canonical Ltd.  All rights reserved.
"""queue tool base class tests."""

__metaclass__ = type

import os
import shutil
from unittest import TestCase, TestLoader

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces import (
    IDistributionSet, IDistroReleaseQueueSet)
from canonical.launchpad.scripts.queue import (
    CommandRunner, CommandRunnerError, name_queue_map)
from canonical.lp.dbschema import (
    PackagePublishingStatus, PackagePublishingPocket,
    DistroReleaseQueueStatus)
from canonical.testing import LaunchpadZopelessLayer


class TestQueueBase:
    """Base methods for queue tool test classes."""

    def _update_file_watch(self):
        """Update new file registers."""
        current = os.listdir('.')
        self.new_files = [f for f in current if f not in self.old_files]

    def _remove_new_files(self):
        """Remove new files from disk"""
        for f in self.new_files:
            os.remove(f)
        self._reset_file_watch()

    def _reset_file_watch(self):
        """Clean new file registers """
        self.new_files = []
        self.old_files = os.listdir('.')

    def _test_display(self, text):
        """Store output from queue tool for inspection."""
        self.test_output.append(text)

    def _fill_librarian_file(self, fileid, content='Fake Content'):
        """Write contents in disk for a librarian sampledata."""
        libpath = '/var/tmp/fatsam.test/'

        full_id = "%08x" % int(fileid)
        dirpath = '%s/%s/%s' % (full_id[:2], full_id[2:4], full_id[4:6])

        libpath = os.path.join(libpath, dirpath)
        if not os.path.exists(libpath):
            os.makedirs(libpath)

        libpath = os.path.join(libpath, full_id[6:])
        libfile = open(libpath, 'wb')
        libfile.write(content)
        libfile.close()

    def _remove_librarian_file(self, fileid):
        """Remove the path for pre-filled librarian sampledata"""
        libpath = '/var/tmp/fatsam.test/'
        full_id = "%08x" % int(fileid)
        dirpath = '%s' % (full_id[:2])
        libpath = os.path.join(libpath, dirpath)
        if not os.path.exists(libpath):
            shutil.rmtree(libpath)

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
        self._fill_librarian_file(1)
        self._fill_librarian_file(52)
        self._reset_file_watch()

    def tearDown(self):
        """Remove test contents from disk."""
        self._remove_librarian_file(1)
        self._remove_librarian_file(52)
        self._remove_new_files()

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

    def testAcceptionWorkflowForDuplications(self):
        """Check how queue tool behaves dealing with duplicated entries.

        Sampledata provides a duplication of cnews_1.0 in breezy-autotest
        UNAPPROVED queue.

        1 Failed to accept both, only the oldest get accepted
        2 Failed to re-accept the remaining item
        3 Failed to re-accept the remaing item even when former is DONE
        4 Successfully rejection of the remaining item
        """
        bat = getUtility(IDistributionSet)['ubuntu']['breezy-autotest']

        # 'cnews' upload duplication in UNAPPROVED
        self.assertEqual(2, bat.getQueueItems(
            status=DistroReleaseQueueStatus.UNAPPROVED, name="cnews").count())

        # try to accept both
        queue_action = self.execute_command(
            'accept cnews', queue_name='unapproved',
            suite_name='breezy-autotest')

        # the first is in accepted.
        self.assertEqual(1, bat.getQueueItems(
            status=DistroReleaseQueueStatus.ACCEPTED, name="cnews").count())
        # the last can't be accepted and remains in UNAPPROVED
        self.assertTrue(
            ('** cnews could not be accepted due This '
             'sourcepackagerelease is already accepted in breezy-autotest.')
            in self.test_output)
        self.assertEqual(1, bat.getQueueItems(
            status=DistroReleaseQueueStatus.UNAPPROVED, name="cnews").count())

        # try to accept the remaining item in UNAPPROVED.
        queue_action = self.execute_command(
            'accept cnews', queue_name='unapproved',
            suite_name='breezy-autotest')
        self.assertTrue(
            ('** cnews could not be accepted due This '
             'sourcepackagerelease is already accepted in breezy-autotest.')
            in self.test_output)
        self.assertEqual(1, bat.getQueueItems(
            status=DistroReleaseQueueStatus.UNAPPROVED, name="cnews").count())

        # simulate a publication of the accepted item, now it is in DONE
        accepted_item = bat.getQueueItems(
            status=DistroReleaseQueueStatus.ACCEPTED, name="cnews")[0]
        accepted_item.setDone()
        accepted_item.syncUpdate()
        self.assertEqual(1, bat.getQueueItems(
            status=DistroReleaseQueueStatus.DONE, name="cnews").count())

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
        self.assertEqual(1, bat.getQueueItems(
            status=DistroReleaseQueueStatus.UNAPPROVED, name="cnews").count())

        # The only possible destiny for the remaining item it REJECT
        queue_action = self.execute_command(
            'reject cnews', queue_name='unapproved',
            suite_name='breezy-autotest')
        self.assertEqual(0, bat.getQueueItems(
            status=DistroReleaseQueueStatus.UNAPPROVED, name="cnews").count())
        self.assertEqual(1, bat.getQueueItems(
            status=DistroReleaseQueueStatus.REJECTED, name="cnews").count())

    def testZZZFetchActionDoNotOverwriteFilesystem(self):
        """ """
        queue_action = self.execute_command('fetch 1')
        self._update_file_watch()
        self.assertEqual(['mozilla-firefox_0.9_i386.changes'], self.new_files)

        # fetch will raise and not overwrite the file in disk
        self.assertRaises(
            CommandRunnerError, self.execute_command, 'fetch 1')
        self._remove_new_files()

        # after removing the file in disk queue will work as expected
        queue_action = self.execute_command('fetch 1')
        self._update_file_watch()
        self.assertEqual(['mozilla-firefox_0.9_i386.changes'], self.new_files)
        self._remove_new_files()

        # sampledata provides duplicated cnews entries
        # queue will download the oldest and raise
        self.assertRaises(
            CommandRunnerError, self.execute_command,
            'fetch cnews', queue_name='unapproved',
            suite_name='breezy-autotest')
        self._update_file_watch()
        self.assertEqual(['netapplet-1.0.0.tar.gz'], self.new_files)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

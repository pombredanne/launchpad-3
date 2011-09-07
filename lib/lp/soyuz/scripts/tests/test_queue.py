# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""queue tool base class tests."""

__metaclass__ = type

import hashlib
import os
import shutil
from StringIO import StringIO
import tempfile
from testtools.matchers import StartsWith
from unittest import TestCase

from zope.component import getUtility
from zope.security.interfaces import ForbiddenAttribute
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.database.librarian import LibraryFileAlias
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.librarian.testing.server import fillLibrarianFile
from canonical.librarian.utils import filechunks
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    LibrarianLayer,
    )
from lp.archiveuploader.nascentupload import NascentUpload
from lp.archiveuploader.tests import (
    datadir,
    getPolicy,
    insertFakeChangesFileForAllPackageUploads,
    )
from lp.bugs.interfaces.bug import IBugSet
from lp.bugs.interfaces.bugtask import (
    BugTaskStatus,
    IBugTaskSet,
    )
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.services.log.logger import DevNullLogger
from lp.services.mail import stub
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    PackageUploadStatus,
    )
from lp.soyuz.interfaces.archive import IArchiveSet
from lp.soyuz.interfaces.queue import IPackageUploadSet
from lp.soyuz.model.queue import PackageUploadBuild
from lp.soyuz.scripts.processaccepted import (
    close_bugs_for_sourcepackagerelease,
    )
from lp.soyuz.scripts.queue import (
    CommandRunner,
    CommandRunnerError,
    name_queue_map,
    QueueAction,
    QueueActionOverride
    )
from lp.testing import (
    celebrity_logged_in,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.fakemethod import FakeMethod


class TestQueueBase:
    """Base methods for queue tool test classes."""

    def setUp(self):
        # Switch database user and set isolation level to READ COMMIITTED
        # to avoid SERIALIZATION exceptions with the Librarian.
        LaunchpadZopelessLayer.switchDbUser(self.dbuser)

    def _test_display(self, text):
        """Store output from queue tool for inspection."""
        self.test_output.append(text)

    def execute_command(self, argument, queue_name='new', no_mail=True,
                        distribution_name='ubuntu', component_name=None,
                        section_name=None, priority_name=None,
                        suite_name='breezy-autotest', quiet=True):
        """Helper method to execute a queue command.

        Initialize output buffer and execute a command according
        given argument.

        Return the used QueueAction instance.
        """
        self.test_output = []
        queue = name_queue_map[queue_name]
        runner = CommandRunner(
            queue, distribution_name, suite_name, no_mail,
            component_name, section_name, priority_name,
            display=self._test_display)

        return runner.execute(argument.split())

    def assertEmail(self, expected_to_addrs):
        """Pop an email from the stub queue and check its recipients."""
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        self.assertEqual(to_addrs, expected_to_addrs)


class TestQueueTool(TestQueueBase, TestCase):
    layer = LaunchpadZopelessLayer
    dbuser = config.uploadqueue.dbuser

    def setUp(self):
        """Create contents in disk for librarian sampledata."""
        # Packageupload.notify() needs real changes file data to send
        # email, so this nice simple "ed" changes file will do.  It's
        # the /wrong/ changes file for the package in the upload queue,
        # but that doesn't matter as only email addresses are parsed out
        # of it.
        insertFakeChangesFileForAllPackageUploads()
        fake_chroot = LibraryFileAlias.get(1)

        LaunchpadZopelessLayer.switchDbUser("testadmin")

        ubuntu = getUtility(IDistributionSet)['ubuntu']
        breezy_autotest = ubuntu.getSeries('breezy-autotest')
        breezy_autotest['i386'].addOrUpdateChroot(fake_chroot)

        LaunchpadZopelessLayer.txn.commit()
        LaunchpadZopelessLayer.switchDbUser('launchpad')

        TestQueueBase.setUp(self)

    def tearDown(self):
        """Remove test contents from disk."""
        LibrarianLayer.librarian_fixture.clear()

    def uploadPackage(self,
            changesfile="suite/bar_1.0-1/bar_1.0-1_source.changes"):
        """Helper function to upload a package."""
        LaunchpadZopelessLayer.switchDbUser("uploader")
        sync_policy = getPolicy(
            name='sync', distro='ubuntu', distroseries='breezy-autotest')
        bar_src = NascentUpload.from_changesfile_path(
            datadir(changesfile),
            sync_policy, DevNullLogger())
        bar_src.process()
        bar_src.do_accept()
        LaunchpadZopelessLayer.txn.commit()
        LaunchpadZopelessLayer.switchDbUser(self.dbuser)
        return bar_src

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
        self.execute_command('help')
        self.assertEqual(
            ['Running: "help"',
             '\tinfo : Present the Queue item including its contents. ',
             '\taccept : Accept the contents of a queue item. ',
             '\treport : Present a report about the size of available '
                  'queues ',
             '\treject : Reject the contents of a queue item. ',
             '\toverride : Override information in a queue item content. ',
             '\tfetch : Fetch the contents of a queue item. '],
            self.test_output)

        self.execute_command('help fetch')
        self.assertEqual(
            ['Running: "help fetch"',
             '\tfetch : Fetch the contents of a queue item. '],
            self.test_output)

        self.execute_command('help foo')
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
        queue_size = getUtility(IPackageUploadSet).count(
            status=PackageUploadStatus.NEW, distroseries=bat,
            pocket=PackagePublishingPocket.RELEASE)
        self.assertEqual(queue_size, queue_action.size)
        # check if none of them was filtered, since not filter term
        # was passed.
        self.assertEqual(queue_size, queue_action.items_size)

    def testInfoActionDoesNotSupportWildCards(self):
        """Check if an wildcard-like filter raises CommandRunnerError."""
        self.assertRaises(
            CommandRunnerError, self.execute_command, 'info *')

    def testInfoActionByID(self):
        """Check INFO queue action filtering by ID.

        It should work as expected in case of existent ID in specified the
        location.
        Otherwise it raises CommandRunnerError if:
         * ID not found
         * specified ID doesn't match given suite name
         * specified ID doesn't match the queue name
        """
        queue_action = self.execute_command('info 1')
        # Check if only one item was retrieved.
        self.assertEqual(1, queue_action.items_size)

        displaynames = [item.displayname for item in queue_action.items]
        self.assertEqual(['mozilla-firefox'], displaynames)

        # Check passing multiple IDs.
        queue_action = self.execute_command('info 1 3 4')
        self.assertEqual(3, queue_action.items_size)
        [mozilla, netapplet, alsa] = queue_action.items
        self.assertEqual('mozilla-firefox', mozilla.displayname)
        self.assertEqual('netapplet', netapplet.displayname)
        self.assertEqual('alsa-utils', alsa.displayname)

        # Check not found ID.
        self.assertRaises(
            CommandRunnerError, self.execute_command, 'info 100')

        # Check looking in the wrong suite.
        self.assertRaises(
            CommandRunnerError, self.execute_command, 'info 1',
            suite_name='breezy-autotest-backports')

        # Check looking in the wrong queue.
        self.assertRaises(
            CommandRunnerError, self.execute_command, 'info 1',
            queue_name='done')

    def testInfoActionByName(self):
        """Check INFO queue action filtering by name"""
        queue_action = self.execute_command('info pmount')
        # check if only one item was retrieved as expected in the current
        # sampledata
        self.assertEqual(1, queue_action.items_size)

        displaynames = [item.displayname for item in queue_action.items]
        self.assertEqual(['pmount'], displaynames)

        # Check looking for multiple names.
        queue_action = self.execute_command('info pmount alsa-utils')
        self.assertEqual(2, queue_action.items_size)
        [pmount, alsa] = queue_action.items
        self.assertEqual('pmount', pmount.displayname)
        self.assertEqual('alsa-utils', alsa.displayname)

    def testAcceptingSourceGeneratesEmail(self):
        """Check if accepting a source package generates an email."""
        # We need to upload a new source package to do this because the
        # sample data is horribly broken with published sources also in
        # the NEW queue.  Doing it this way guarantees a nice set of data.
        self.uploadPackage()

        # Swallow email generated at the upload stage.
        stub.test_emails.pop()

        # Add a chroot to breezy-autotest/i386, so the system can create
        # builds for it.
        LaunchpadZopelessLayer.txn.commit()
        LaunchpadZopelessLayer.switchDbUser("launchpad")

        a_file = getUtility(ILibraryFileAliasSet)[1]
        breezy_autotest = getUtility(
            IDistributionSet)['ubuntu']['breezy-autotest']
        breezy_autotest['i386'].addOrUpdateChroot(a_file)

        LaunchpadZopelessLayer.txn.commit()
        LaunchpadZopelessLayer.switchDbUser(self.dbuser)

        queue_action = self.execute_command(
            'accept bar', no_mail=False)
        self.assertEqual(1, queue_action.items_size)
        self.assertEqual(2, len(stub.test_emails))
        # Emails sent are the announcement and the uploader's notification:
        self.assertEmail(['autotest_changes@ubuntu.com'])
        self.assertEmail(
            ['Daniel Silverstone <daniel.silverstone@canonical.com>'])

    def testAcceptingSourceCreateBuilds(self):
        """Check if accepting a source package creates build records."""
        self.uploadPackage()

        # Swallow email generated at the upload stage.
        stub.test_emails.pop()

        # Add a chroot to breezy-autotest/i386, so the system can create
        # builds for it.
        LaunchpadZopelessLayer.txn.commit()
        LaunchpadZopelessLayer.switchDbUser("launchpad")

        a_file = getUtility(ILibraryFileAliasSet)[1]
        breezy_autotest = getUtility(
            IDistributionSet)['ubuntu']['breezy-autotest']
        breezy_autotest['i386'].addOrUpdateChroot(a_file)

        LaunchpadZopelessLayer.txn.commit()
        LaunchpadZopelessLayer.switchDbUser(self.dbuser)

        queue_action = self.execute_command(
            'accept bar', no_mail=False)
        self.assertEqual(1, queue_action.items_size)
        self.assertEqual(2, len(stub.test_emails))

        [queue_item] = queue_action.items
        [queue_source] = queue_item.sources
        sourcepackagerelease = queue_source.sourcepackagerelease
        [build] = sourcepackagerelease.builds
        self.assertEqual(
            'i386 build of bar 1.0-1 in ubuntu breezy-autotest RELEASE',
            build.title)
        self.assertEqual(build.buildqueue_record.lastscore, 1755)

    def testAcceptingBinaryDoesntGenerateEmail(self):
        """Check if accepting a binary package does not generate email."""
        queue_action = self.execute_command(
            'accept mozilla-firefox', no_mail=False)
        self.assertEqual(1, queue_action.items_size)
        self.assertEqual(0, len(stub.test_emails))

    def testAcceptingSourceClosesBug(self):
        """Check that accepting a source will close bugs appropriately."""
        # To speed up the publication process, single source uploads
        # are automatically published when they are accepted to avoid
        # another publisher cycle's worth of delay.  When the source is
        # published, any bugs mentioned in the upload must be closed.

        # First we must upload the first version of 'bar' in Ubuntu Hoary.
        bar_src = self.uploadPackage()
        bar_src.queue_root.setAccepted()
        bar_src.queue_root.realiseUpload()

        # Now make a new bugtask for the "bar" package.
        LaunchpadZopelessLayer.txn.commit()
        LaunchpadZopelessLayer.switchDbUser("launchpad")

        the_bug_id = 6
        bugtask_owner = getUtility(IPersonSet).getByName('kinnison')
        ubuntu = getUtility(IDistributionSet)['ubuntu']
        ubuntu_bar = ubuntu.getSourcePackage('bar')
        the_bug = getUtility(IBugSet).get(the_bug_id)
        bugtask = getUtility(IBugTaskSet).createTask(
            the_bug, bugtask_owner, ubuntu_bar)

        LaunchpadZopelessLayer.txn.commit()
        LaunchpadZopelessLayer.switchDbUser(self.dbuser)

        # The bugtask starts life as NEW.
        the_bug = getUtility(IBugSet).get(the_bug_id)
        bugtask = the_bug.getBugTask(ubuntu_bar)
        bug_status = bugtask.status.name
        self.assertEqual(
            bug_status, 'NEW',
            'Bug status is %s, expected NEW' % bug_status)

        # Now, make an upload for the next version of "bar".
        bar2_src = self.uploadPackage(
            changesfile="suite/bar_1.0-2/bar_1.0-2_source.changes")

        # Now accept the new bar upload with the queue tool.
        self.execute_command('accept bar', no_mail=False)

        # The upload wants to close bug 6:
        bugs_fixed_header = bar2_src.changes._dict['Launchpad-bugs-fixed']
        self.assertEqual(
            bugs_fixed_header, str(the_bug_id),
            'Expected bug %s in Launchpad-bugs-fixed, got %s'
                % (the_bug_id, bugs_fixed_header))

        # The upload should be in the DONE state:
        item_status = bar2_src.queue_root.status.name
        self.assertEqual(
            item_status, 'DONE',
            'Upload status is %s, expected DONE' % item_status)

        # The bug should now be marked as fix released for the "bar"
        # bugtask:
        the_bug = getUtility(IBugSet).get(the_bug_id)
        bugtask = the_bug.getBugTask(ubuntu_bar)
        bug_status = bugtask.status.name
        self.assertEqual(
            bug_status, 'FIXRELEASED',
            'Bug status is %s, expected FIXRELEASED')

    def testAcceptActionWithMultipleIDs(self):
        """Check if accepting multiple items at once works.

        We can specify multiple items to accept, even mixing IDs and names.
        e.g. queue accept alsa-utils 1 3
        """
        breezy_autotest = getUtility(
            IDistributionSet)['ubuntu']['breezy-autotest']
        queue_action = self.execute_command('accept 1 pmount 3')

        self.assertEqual(3, queue_action.items_size)

        self.assertQueueLength(1, breezy_autotest,
            PackageUploadStatus.ACCEPTED, u'mozilla-firefox')
        self.assertQueueLength(1, breezy_autotest,
            PackageUploadStatus.ACCEPTED, u'pmount')
        # Single-source upload went straight to DONE queue.
        self.assertQueueLength(1, breezy_autotest,
            PackageUploadStatus.DONE, u'netapplet')

    def testRemovedPublishRecordDoesNotAffectQueueNewness(self):
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
        self.assertEqual(PackagePublishingStatus.DELETED,
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

    def testQueueDoesNotAnnounceBackports(self):
        """Check if BACKPORTS acceptance are not announced publicly.

        Queue tool normally announce acceptance in the specified changeslist
        for the distroseries in question, however BACKPORTS announce doesn't
        fit very well in that list, they cause unwanted noise.

        Further details in bug #59443
        """
        LaunchpadZopelessLayer.switchDbUser("launchpad")

        # Make breezy-autotest CURRENT in order to accept upload
        # to BACKPORTS.
        breezy_autotest = getUtility(
            IDistributionSet)['ubuntu']['breezy-autotest']
        breezy_autotest.status = SeriesStatus.CURRENT

        LaunchpadZopelessLayer.txn.commit()
        LaunchpadZopelessLayer.switchDbUser(self.dbuser)

        # Store the targeted queue item for future inspection.
        # Ensure it is what we expect.
        target_queue = breezy_autotest.getPackageUploads(
            status=PackageUploadStatus.UNAPPROVED,
            pocket=PackagePublishingPocket.BACKPORTS)[0]
        self.assertEqual(10, target_queue.id)

        # Ensure breezy-autotest is set.
        self.assertEqual(
            u'autotest_changes@ubuntu.com', breezy_autotest.changeslist)

        # Accept the sampledata item.
        queue_action = self.execute_command(
            'accept', queue_name='unapproved',
            suite_name='breezy-autotest-backports', no_mail=False)

        # Only one item considered.
        self.assertEqual(1, queue_action.items_size)

        # Previously stored reference should have new state now
        self.assertEqual('ACCEPTED', target_queue.status.name)

        # Only one email is sent to the changed-by email on the changes
        # file.  No announcement email is sent.
        self.assertEqual(len(stub.test_emails), 1)
        self.assertEmail(
            ['Daniel Silverstone <daniel.silverstone@canonical.com>'])

    def testQueueDoesNotSendAnyEmailsForTranslations(self):
        """Check if no emails are sent when accepting translations.

        Queue tool should not send any emails to source uploads targeted to
        'translation' section.
        They are the 'language-pack-*' and 'language-support-*' sources.

        Further details in bug #57708
        """
        LaunchpadZopelessLayer.switchDbUser("launchpad")

        # Make breezy-autotest CURRENT in order to accept upload
        # to PROPOSED.
        breezy_autotest = getUtility(
            IDistributionSet)['ubuntu']['breezy-autotest']
        breezy_autotest.status = SeriesStatus.CURRENT

        LaunchpadZopelessLayer.txn.commit()
        LaunchpadZopelessLayer.switchDbUser(self.dbuser)

        # Store the targeted queue item for future inspection.
        # Ensure it is what we expect.
        target_queue = breezy_autotest.getPackageUploads(
            status=PackageUploadStatus.UNAPPROVED,
            pocket=PackagePublishingPocket.PROPOSED)[0]
        self.assertEqual(12, target_queue.id)
        source = target_queue.sources[0].sourcepackagerelease
        self.assertEqual('translations', source.section.name)

        # Accept the sampledata item.
        queue_action = self.execute_command(
            'accept', queue_name='unapproved',
            suite_name='breezy-autotest-proposed', no_mail=False)

        # Only one item considered.
        self.assertEqual(1, queue_action.items_size)

        # Previously stored reference should have new state now.
        self.assertEqual('DONE', target_queue.status.name)

        # No email was sent.
        self.assertEqual(0, len(stub.test_emails))

    def assertQueueLength(self, expected_length, distro_series, status, name):
        queue_items = distro_series.getPackageUploads(
            status=status, name=name)
        self.assertEqual(expected_length, queue_items.count())

    def assertErrorAcceptingDuplicate(self):
        self.assertTrue(
            '** cnews could not be accepted due to '
            'The source cnews - 1.0 is already accepted in ubuntu/'
            'breezy-autotest and you cannot upload the same version '
            'within the same distribution. You have to modify the source '
            'version and re-upload.' in self.test_output)

    def testAcceptanceWorkflowForDuplications(self):
        """Check how queue tool behaves dealing with duplicated entries.

        Sampledata provides a duplication of cnews_1.0 in breezy-autotest
        UNAPPROVED queue.

        Step 1:  executing 'accept cnews in unapproved queue' with duplicate
        cnews items in the UNAPPROVED queue, results in the oldest being
        accepted and the newer one remaining UNAPPROVED (and displaying
        an error about it to the user).

        Step 2: executing 'accept cnews in unapproved queue' with duplicate
        cnews items in the UNAPPROVED and ACCEPTED queues has no effect on
        the queues, and again displays an error to the user.

        Step 3: executing 'accept cnews in unapproved queue' with duplicate
        cnews items in the UNAPPROVED and DONE queues behaves the same as 2.

        Step 4: the remaining duplicated cnews item in UNAPPROVED queue can
        only be rejected.
        """
        LaunchpadZopelessLayer.switchDbUser("launchpad")

        # Add a chroot to breezy-autotest/i386, so the system can create
        # builds for it.
        a_file = getUtility(ILibraryFileAliasSet)[1]
        breezy_autotest = getUtility(
            IDistributionSet)['ubuntu']['breezy-autotest']
        breezy_autotest['i386'].addOrUpdateChroot(a_file)

        LaunchpadZopelessLayer.txn.commit()
        LaunchpadZopelessLayer.switchDbUser(self.dbuser)

        # Certify we have a 'cnews' upload duplication in UNAPPROVED.
        self.assertQueueLength(
            2, breezy_autotest, PackageUploadStatus.UNAPPROVED, u"cnews")

        # Step 1: try to accept both.
        self.execute_command(
            'accept cnews', queue_name='unapproved',
            suite_name='breezy-autotest')

        # The first item, being a single source upload, is automatically
        # published when it's accepted.
        self.assertQueueLength(
            1, breezy_autotest, PackageUploadStatus.DONE, u"cnews")

        # The last can't be accepted and remains in UNAPPROVED.
        self.assertErrorAcceptingDuplicate()
        self.assertQueueLength(
            1, breezy_autotest, PackageUploadStatus.UNAPPROVED, u"cnews")

        # Step 2: try to accept the remaining item in UNAPPROVED.
        self.execute_command(
            'accept cnews', queue_name='unapproved',
            suite_name='breezy-autotest')
        self.assertErrorAcceptingDuplicate()
        self.assertQueueLength(
            1, breezy_autotest, PackageUploadStatus.UNAPPROVED, u"cnews")

        # Step 3: try to accept the remaining item in UNAPPROVED with the
        # duplication already in DONE.
        self.execute_command(
            'accept cnews', queue_name='unapproved',
            suite_name='breezy-autotest')
        # It failed and te item remains in UNAPPROVED.
        self.assertErrorAcceptingDuplicate()
        self.assertQueueLength(
            1, breezy_autotest, PackageUploadStatus.UNAPPROVED, u"cnews")

        # Step 4: The only possible destiny for the remaining item it REJECT.
        self.execute_command(
            'reject cnews', queue_name='unapproved',
            suite_name='breezy-autotest')
        self.assertQueueLength(
            0, breezy_autotest, PackageUploadStatus.UNAPPROVED, u"cnews")
        self.assertQueueLength(
            1, breezy_autotest, PackageUploadStatus.REJECTED, u"cnews")

    def testRejectSourceSendsEmail(self):
        """Check that rejecting a source upload sends email."""
        queue_action = self.execute_command(
            'reject alsa-utils', no_mail=False)
        self.assertEqual(1, queue_action.items_size)
        self.assertEqual(1, len(stub.test_emails))
        self.assertEmail(
            ['Daniel Silverstone <daniel.silverstone@canonical.com>'])

    def testRejectBinarySendsEmail(self):
        """Check that rejecting a binary upload sends email."""
        queue_action = self.execute_command('reject 2', no_mail=False)
        self.assertEqual(1, queue_action.items_size)
        self.assertEqual(1, len(stub.test_emails))
        self.assertEmail(
            ['Daniel Silverstone <daniel.silverstone@canonical.com>'])

    def testRejectLangpackSendsNoEmail(self):
        """Check that rejecting a language pack sends no email."""
        queue_action = self.execute_command(
            'reject language-pack-de', queue_name='unapproved',
            suite_name='breezy-autotest-proposed')
        self.assertEqual(1, queue_action.items_size)
        self.assertEqual(0, len(stub.test_emails))

    def testRejectWithMultipleIDs(self):
        """Check if rejecting multiple items at once works.

        We can specify multiple items to reject, even mixing IDs and names.
        e.g. queue reject alsa-utils 1 3
        """
        breezy_autotest = getUtility(
            IDistributionSet)['ubuntu']['breezy-autotest']

        # Run the command.
        queue_action = self.execute_command('reject 1 pmount 3')

        # Test what it did.  Since all the queue items came out of the
        # NEW queue originally, the items processed should now be REJECTED.
        self.assertEqual(3, queue_action.items_size)
        self.assertQueueLength(1, breezy_autotest,
            PackageUploadStatus.REJECTED, u'mozilla-firefox')
        self.assertQueueLength(1, breezy_autotest,
            PackageUploadStatus.REJECTED, u'pmount')
        self.assertQueueLength(1, breezy_autotest,
            PackageUploadStatus.REJECTED, u'netapplet')

    def testOverrideSource(self):
        """Check if overriding sources works.

        We can specify multiple items to override, even mixing IDs and names.
        e.g. queue override source -c restricted alsa-utils 1 3
        """
        # Set up.
        breezy_autotest = getUtility(
            IDistributionSet)['ubuntu']['breezy-autotest']

        # Basic operation overriding a single source 'alsa-utils' that
        # is currently main/base in the sample data.
        queue_action = self.execute_command('override source 4',
            component_name='restricted', section_name='web')
        self.assertEqual(1, queue_action.items_size)
        queue_item = breezy_autotest.getPackageUploads(
            status=PackageUploadStatus.NEW, name=u"alsa-utils")[0]
        [source] = queue_item.sources
        self.assertEqual('restricted',
            source.sourcepackagerelease.component.name)
        self.assertEqual('web',
            source.sourcepackagerelease.section.name)

        # Override multiple sources at once and mix ID with name.
        queue_action = self.execute_command('override source 4 netapplet',
            component_name='universe', section_name='editors')
        # 'netapplet' appears 3 times, alsa-utils once.
        self.assertEqual(4, queue_action.items_size)
        self.assertEqual(2, queue_action.overrides_performed)
        # Check results.
        queue_items = list(breezy_autotest.getPackageUploads(
            status=PackageUploadStatus.NEW, name=u'alsa-utils'))
        queue_items.extend(list(breezy_autotest.getPackageUploads(
            status=PackageUploadStatus.NEW, name=u'netapplet')))
        for queue_item in queue_items:
            if queue_item.sources:
                [source] = queue_item.sources
                self.assertEqual('universe',
                    source.sourcepackagerelease.component.name)
                self.assertEqual('editors',
                    source.sourcepackagerelease.section.name)

    def testOverrideSourceWithArchiveChange(self):
        """Check if the archive changes as necessary on a source override.

        When overriding the component, the archive may change, so we check
        that here.
        """
        # Set up.
        ubuntu = getUtility(IDistributionSet)['ubuntu']
        breezy_autotest = ubuntu['breezy-autotest']

        # Test that it changes to partner when required.
        queue_action = self.execute_command('override source alsa-utils',
            component_name='partner')
        self.assertEqual(1, queue_action.items_size)
        [queue_item] = breezy_autotest.getPackageUploads(
            status=PackageUploadStatus.NEW, name=u"alsa-utils")
        [source] = queue_item.sources
        self.assertEqual(source.sourcepackagerelease.upload_archive.purpose,
            ArchivePurpose.PARTNER)

        # Test that it changes back to primary when required.
        queue_action = self.execute_command('override source alsa-utils',
            component_name='main')
        self.assertEqual(1, queue_action.items_size)
        [queue_item] = breezy_autotest.getPackageUploads(
            status=PackageUploadStatus.NEW, name=u"alsa-utils")
        [source] = queue_item.sources
        self.assertEqual(source.sourcepackagerelease.upload_archive.purpose,
            ArchivePurpose.PRIMARY)

    def testOverrideSourceWithNonexistentArchiveChange(self):
        """Check that overriding to a non-existent archive fails properly.

        When overriding the component, the archive may change to a
        non-existent one so ensure if fails.
        """
        LaunchpadZopelessLayer.switchDbUser("launchpad")

        ubuntu = getUtility(IDistributionSet)['ubuntu']
        proxied_archive = getUtility(IArchiveSet).getByDistroPurpose(
            ubuntu, ArchivePurpose.PARTNER)
        comm_archive = removeSecurityProxy(proxied_archive)
        comm_archive.purpose = ArchivePurpose.PPA
        LaunchpadZopelessLayer.txn.commit()
        LaunchpadZopelessLayer.switchDbUser(self.dbuser)

        self.assertRaises(CommandRunnerError,
                          self.execute_command,
                          'override source alsa-utils',
                          component_name='partner')

    def testOverrideBinary(self):
        """Check if overriding binaries works.

        We can specify multiple items to override, even mixing IDs and names.
        e.g. queue override binary -c restricted alsa-utils 1 3
        """
        # Set up.
        breezy_autotest = getUtility(
            IDistributionSet)['ubuntu']['breezy-autotest']

        # Override a binary, 'pmount', from its sample data of
        # main/base/IMPORTANT to restricted/web/extra.
        queue_action = self.execute_command('override binary pmount',
            component_name='restricted', section_name='web',
            priority_name='extra')
        self.assertEqual(1, queue_action.items_size)
        [queue_item] = breezy_autotest.getPackageUploads(
            status=PackageUploadStatus.NEW, name=u"pmount")
        [packagebuild] = queue_item.builds
        for package in packagebuild.build.binarypackages:
            self.assertEqual('restricted', package.component.name)
            self.assertEqual('web', package.section.name)
            self.assertEqual('EXTRA', package.priority.name)

        # Override multiple binaries at once.
        queue_action = self.execute_command(
            'override binary pmount mozilla-firefox',
            component_name='universe', section_name='editors',
            priority_name='optional')
        # Check results.
        self.assertEqual(2, queue_action.items_size)
        self.assertEqual(2, queue_action.overrides_performed)
        queue_items = list(breezy_autotest.getPackageUploads(
            status=PackageUploadStatus.NEW, name=u'pmount'))
        queue_items.extend(list(breezy_autotest.getPackageUploads(
            status=PackageUploadStatus.NEW, name=u'mozilla-firefox')))
        for queue_item in queue_items:
            [packagebuild] = queue_item.builds
            for package in packagebuild.build.binarypackages:
                self.assertEqual('universe', package.component.name)
                self.assertEqual('editors', package.section.name)
                self.assertEqual('OPTIONAL', package.priority.name)

        # Check that overriding by ID is warned to the user.
        self.assertRaises(
            CommandRunnerError, self.execute_command, 'override binary 1',
            component_name='multiverse')

    def testOverridingMulipleBinariesFromSameBuild(self):
        """Check that multiple binary override works for the same build.

        Overriding binary packages generated from the same build should
        override each package individually.
        """
        # Start off by setting up a packageuploadbuild that points to
        # a build with two binaries.
        LaunchpadZopelessLayer.switchDbUser("launchpad")

        breezy_autotest = getUtility(
            IDistributionSet)['ubuntu']['breezy-autotest']
        [mozilla_queue_item] = breezy_autotest.getPackageUploads(
            status=PackageUploadStatus.NEW, name=u'mozilla-firefox')

        # The build with ID '2' is for mozilla-firefox, which produces
        # binaries for 'mozilla-firefox' and 'mozilla-firefox-data'.
        PackageUploadBuild(packageupload=mozilla_queue_item, build=2)

        # Switching db users starts a new transaction.  We must re-fetch
        # breezy-autotest.
        LaunchpadZopelessLayer.txn.commit()
        LaunchpadZopelessLayer.switchDbUser("queued")
        breezy_autotest = getUtility(
            IDistributionSet)['ubuntu']['breezy-autotest']

        queue_action = self.execute_command(
            'override binary mozilla-firefox-data mozilla-firefox',
            component_name='restricted', section_name='editors',
            priority_name='optional')

        # There are three binaries to override on this PackageUpload:
        #  - mozilla-firefox in breezy-autotest
        #  - mozilla-firefox and mozilla-firefox-data in warty
        # Each should be overridden exactly once.
        self.assertEqual(1, queue_action.items_size)
        self.assertEqual(3, queue_action.overrides_performed)

        queue_items = list(breezy_autotest.getPackageUploads(
            status=PackageUploadStatus.NEW, name=u'mozilla-firefox-data'))
        queue_items.extend(list(breezy_autotest.getPackageUploads(
            status=PackageUploadStatus.NEW, name=u'mozilla-firefox')))
        for queue_item in queue_items:
            for packagebuild in queue_item.builds:
                for package in packagebuild.build.binarypackages:
                    self.assertEqual(
                        'restricted', package.component.name,
                        "The component '%s' is not the expected 'restricted'"
                        "for package %s" % (
                            package.component.name, package.name))
                    self.assertEqual(
                        'editors', package.section.name,
                        "The section '%s' is not the expected 'editors'"
                        "for package %s" % (
                            package.section.name, package.name))
                    self.assertEqual(
                        'OPTIONAL', package.priority.name,
                        "The priority '%s' is not the expected 'OPTIONAL'"
                        "for package %s" % (
                            package.section.name, package.name))

    def testOverrideBinaryWithArchiveChange(self):
        """Check if archive changes are disallowed for binary overrides.

        When overriding the component, the archive may change, so we check
        that here and make sure it's disallowed.
        """
        # Test that it changes to partner when required.
        self.assertRaises(
            CommandRunnerError, self.execute_command,
            'override binary pmount', component_name='partner')


class TestQueueActionLite(TestCaseWithFactory):
    """A lightweight unit test case for `QueueAction`.

    Meant for detailed tests that would be too expensive for full end-to-end
    tests.
    """

    layer = LaunchpadZopelessLayer

    def makeQueueAction(self, package_upload, distroseries=None,
                        component=None, section=None,
                        action_type=QueueAction):
        """Create a `QueueAction` for use with a `PackageUpload`.

        The action's `display` method is set to a `FakeMethod`.
        """
        if distroseries is None:
            distroseries = self.factory.makeDistroSeries(
                status=SeriesStatus.CURRENT,
                name="distroseriestestingpcjs")
        distro = distroseries.distribution
        if package_upload is None:
            package_upload = self.factory.makePackageUpload(
                distroseries=distroseries, archive=distro.main_archive)
        if component is None:
            component = self.factory.makeComponent()
        if section is None:
            section = self.factory.makeSection()
        queue = PackageUploadStatus.NEW
        priority_name = "STANDARD"
        display = FakeMethod()
        terms = ['*']
        return action_type(
            distro.name, distroseries.name, queue, terms, component.name,
            section.name, priority_name, display)

    def makeQueueActionOverride(self, package_upload, component, section,
                                distroseries=None):
        return self.makeQueueAction(
            package_upload, distroseries, component, section,
            action_type=QueueActionOverride)

    def parseUploadSummaryLine(self, output_line):
        """Parse an output line from `QueueAction.displayItem`.

        :param output_line: A line of output text from `displayItem`.
        :return: A tuple of displayed items: (id, tag, name, version, age).
        """
        return tuple(item.strip() for item in output_line.split('|'))

    def test_display_actions_have_privileges_for_PackageCopyJob(self):
        # The methods that display uploads have privileges to work with
        # a PackageUpload that has a copy job.
        # Bundling tests for multiple operations into one test because
        # the database user change requires a costly commit.
        upload = self.factory.makeCopyJobPackageUpload()
        action = self.makeQueueAction(upload)
        self.layer.txn.commit()
        self.layer.switchDbUser(config.uploadqueue.dbuser)

        action.displayItem(upload)
        self.assertNotEqual(0, action.display.call_count)
        action.display.calls = []
        action.displayInfo(upload)
        self.assertNotEqual(0, action.display.call_count)

    def test_accept_actions_have_privileges_for_PackageCopyJob(self):
        # The script also has privileges to approve uploads that have
        # copy jobs.
        distroseries = self.factory.makeDistroSeries(
            status=SeriesStatus.CURRENT)
        upload = self.factory.makeCopyJobPackageUpload(distroseries)
        self.layer.txn.commit()
        self.layer.switchDbUser(config.uploadqueue.dbuser)
        upload.acceptFromQueue(DevNullLogger(), dry_run=True)
        # Flush changes to make sure we're not caching any updates that
        # the database won't allow.  If this passes, we've got the
        # privileges.
        IStore(upload).flush()

    def test_displayItem_displays_PackageUpload_with_source(self):
        # displayItem can display a source package upload.
        upload = self.factory.makeSourcePackageUpload()
        action = self.makeQueueAction(upload)

        action.displayItem(upload)

        ((output, ), kwargs) = action.display.calls[0]
        (upload_id, tag, name, version, age) = self.parseUploadSummaryLine(
            output)
        self.assertEqual(str(upload.id), upload_id)
        self.assertEqual("S-", tag)
        self.assertThat(upload.displayname, StartsWith(name))
        self.assertThat(upload.package_version, StartsWith(version))

    def test_displayItem_displays_PackageUpload_with_PackageCopyJob(self):
        # displayItem can display a copy-job package upload.
        upload = self.factory.makeCopyJobPackageUpload()
        action = self.makeQueueAction(upload)

        action.displayItem(upload)

        ((output, ), kwargs) = action.display.calls[0]
        (upload_id, tag, name, version, age) = self.parseUploadSummaryLine(
            output)
        self.assertEqual(str(upload.id), upload_id)
        self.assertEqual("X-", tag)
        self.assertThat(upload.displayname, StartsWith(name))
        self.assertThat(upload.package_version, StartsWith(version))

    def test_override_works_with_PackageCopyJob(self):
        # "Sync" PackageUploads can be overridden just like sources,
        # test that here.
        new_component = self.factory.makeComponent()
        new_section = self.factory.makeSection()
        pocket = PackagePublishingPocket.RELEASE
        upload = self.factory.makeCopyJobPackageUpload(target_pocket=pocket)
        action = self.makeQueueActionOverride(
            upload, new_component, new_section,
            distroseries=upload.distroseries)
        # Patch this out because it uses data we don't have in the test;
        # it's unnecessary anyway.
        self.patch(action, "displayTitle", FakeMethod)
        action.terms = ["source", str(upload.id)]
        self.layer.txn.commit()
        self.layer.switchDbUser(config.uploadqueue.dbuser)
        action.initialize()
        action.run()

        # Overriding a sync means putting the overrides in the job itself.
        self.assertEqual(
            new_component.name, upload.package_copy_job.component_name)
        self.assertEqual(
            new_section.name, upload.package_copy_job.section_name)

    def test_makeTag_returns_S_for_source_upload(self):
        upload = self.factory.makeSourcePackageUpload()
        self.assertEqual('S-', self.makeQueueAction(upload)._makeTag(upload))

    def test_makeTag_returns_B_for_binary_upload(self):
        upload = self.factory.makeBuildPackageUpload()
        self.assertEqual('-B', self.makeQueueAction(upload)._makeTag(upload))

    def test_makeTag_returns_SB_for_mixed_upload(self):
        upload = self.factory.makeSourcePackageUpload()
        upload.addBuild(self.factory.makeBinaryPackageBuild())
        self.assertEqual('SB', self.makeQueueAction(upload)._makeTag(upload))

    def test_makeTag_returns_X_for_copy_job_upload(self):
        upload = self.factory.makeCopyJobPackageUpload()
        self.assertEqual('X-', self.makeQueueAction(upload)._makeTag(upload))

    def test_makeTag_returns_dashes_for_custom_upload(self):
        upload = self.factory.makeCustomPackageUpload()
        self.assertEqual('--', self.makeQueueAction(upload)._makeTag(upload))

    def test_displayInfo_displays_PackageUpload_with_source(self):
        # displayInfo can display a source package upload.
        upload = self.factory.makeSourcePackageUpload()
        action = self.makeQueueAction(upload)
        action.displayInfo(upload)
        self.assertNotEqual(0, action.display.call_count)

    def test_displayInfo_displays_PackageUpload_with_PackageCopyJob(self):
        # displayInfo can display a copy-job package upload.
        upload = self.factory.makeCopyJobPackageUpload()
        action = self.makeQueueAction(upload)
        action.displayInfo(upload)
        self.assertNotEqual(0, action.display.call_count)


class TestQueuePageClosingBugs(TestCaseWithFactory):
    # The distroseries +queue page can close bug when accepting
    # packages.  Unit tests for that belong here.

    layer = DatabaseFunctionalLayer

    def test_close_bugs_for_sourcepackagerelease_with_private_bug(self):
        # lp.soyuz.scripts.processaccepted.close_bugs_for_sourcepackagerelease
        # should work with private bugs where the person using the queue
        # page doesn't have access to it.
        changes_file_template = "Format: 1.7\nLaunchpad-bugs-fixed: %s\n"
        # changelog_entry is required for an assertion inside the function
        # we're testing.
        spr = self.factory.makeSourcePackageRelease(changelog_entry="blah")
        archive_admin = self.factory.makePerson()
        bug = self.factory.makeBug(private=True)
        bug_task = self.factory.makeBugTask(target=spr.sourcepackage, bug=bug)
        changes = StringIO(changes_file_template % bug.id)

        with person_logged_in(archive_admin):
            # The archive admin user can't normally see this bug.
            self.assertRaises(ForbiddenAttribute, bug, 'status')
            # But the bug closure should work.
            close_bugs_for_sourcepackagerelease(spr, changes)

        # Verify it was closed.
        with celebrity_logged_in("admin"):
            self.assertEqual(bug_task.status, BugTaskStatus.FIXRELEASED)


class TestQueueToolInJail(TestQueueBase, TestCase):
    layer = LaunchpadZopelessLayer
    dbuser = config.uploadqueue.dbuser

    def setUp(self):
        """Create contents in disk for librarian sampledata.

        Setup and chdir into a temp directory, a jail, where we can
        control the file creation properly
        """
        fillLibrarianFile(1, content='One')
        fillLibrarianFile(52, content='Fifty-Two')
        self._home = os.path.abspath('')
        self._jail = tempfile.mkdtemp()
        os.chdir(self._jail)
        TestQueueBase.setUp(self)

    def tearDown(self):
        """Remove test contents from disk.

        chdir back to the previous path (home) and remove the temp
        directory used as jail.
        """
        os.chdir(self._home)
        LibrarianLayer.librarian_fixture.clear()
        shutil.rmtree(self._jail)

    def _listfiles(self):
        """Return a list of files present in jail."""
        return os.listdir(self._jail)

    def _getsha1(self, filename):
        """Return a sha1 hex digest of a file"""
        file_sha = hashlib.sha1()
        opened_file = open(filename, "r")
        for chunk in filechunks(opened_file):
            file_sha.update(chunk)
        opened_file.close()
        return file_sha.hexdigest()

    def testFetchActionByIDDoNotOverwriteFilesystem(self):
        """Check if queue fetch action doesn't overwrite files.

        Since we allow existence of duplications in NEW and UNAPPROVED
        queues, we are able to fetch files from queue items and they'd
        get overwritten causing obscure problems.

        Instead of overwrite a file in the working directory queue will
        fail, raising a CommandRunnerError.

        bug 67014: Don't complain if files are the same
        """
        self.execute_command('fetch 1')
        self.assertEqual(
            ['mozilla-firefox_0.9_i386.changes'], self._listfiles())

        # checksum the existing file
        existing_sha1 = self._getsha1(self._listfiles()[0])

        # fetch will NOT raise and not overwrite the file in disk
        self.execute_command('fetch 1')

        # checksum file again
        new_sha1 = self._getsha1(self._listfiles()[0])

        # Check that the file has not changed (we don't care if it was
        # re-written, just that it's not changed)
        self.assertEqual(existing_sha1, new_sha1)

    def testFetchActionRaisesErrorIfDifferentFileAlreadyFetched(self):
        """Check that fetching a file that has already been fetched
        raises an error if they are not the same file.  (bug 67014)
        """
        CLOBBERED = "you're clobbered"

        self.execute_command('fetch 1')
        self.assertEqual(
            ['mozilla-firefox_0.9_i386.changes'], self._listfiles())

        # clobber the existing file, fetch it again and expect an exception
        f = open(self._listfiles()[0], "w")
        f.write(CLOBBERED)
        f.close()

        self.assertRaises(
            CommandRunnerError, self.execute_command, 'fetch 1')

        # make sure the file has not changed
        f = open(self._listfiles()[0], "r")
        line = f.read()
        f.close()

        self.assertEqual(CLOBBERED, line)

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

    def testQueueFetch(self):
        """Check that a basic fetch operation works."""
        FAKE_CHANGESFILE_CONTENT = "Fake Changesfile"
        FAKE_DEB_CONTENT = "Fake DEB"
        fillLibrarianFile(1, FAKE_CHANGESFILE_CONTENT)
        fillLibrarianFile(90, FAKE_DEB_CONTENT)
        self.execute_command('fetch pmount')

        # Check the files' names.
        files = sorted(self._listfiles())
        self.assertEqual(
            ['netapplet-1.0.0.tar.gz', 'pmount_1.0-1_all.deb'],
            files)

        # Check the files' contents.
        changes_file = open('netapplet-1.0.0.tar.gz')
        self.assertEqual(changes_file.read(), FAKE_CHANGESFILE_CONTENT)
        changes_file.close()
        debfile = open('pmount_1.0-1_all.deb')
        self.assertEqual(debfile.read(), FAKE_DEB_CONTENT)
        debfile.close()

    def testFetchMultipleItems(self):
        """Check if fetching multiple items at once works.

        We can specify multiple items to fetch, even mixing IDs and names.
        e.g. queue fetch alsa-utils 1 3
        """
        self.execute_command('fetch 3 mozilla-firefox')
        files = self._listfiles()
        files.sort()
        self.assertEqual(
            ['mozilla-firefox_0.9_i386.changes', 'netapplet-1.0.0.tar.gz'],
            files)

# Copyright 2006 Canonical Ltd.  All rights reserved.
"""queue tool base class tests."""

__metaclass__ = type

import os
import shutil
import tempfile
from unittest import TestCase, TestLoader
from sha import sha

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.archiveuploader.tests import datadir
from canonical.config import config
from canonical.database.sqlbase import READ_COMMITTED_ISOLATION
from canonical.launchpad.interfaces import (
    IArchiveSet, IDistributionSet, IPackageUploadSet)
from canonical.launchpad.mail import stub
from canonical.launchpad.scripts.queue import (
    CommandRunner, CommandRunnerError, name_queue_map)
from canonical.librarian.ftests.harness import (
    fillLibrarianFile, cleanupLibrarianFiles)
from canonical.lp.dbschema import (
    ArchivePurpose, PackagePublishingStatus, PackagePublishingPocket,
    PackageUploadStatus, DistroSeriesStatus)
from canonical.testing import LaunchpadZopelessLayer
from canonical.librarian.utils import filechunks


class TestQueueBase(TestCase):
    """Base methods for queue tool test classes."""

    def setUp(self):
        # Switch database user and set isolation level to READ COMMIITTED
        # to avoid SERIALIZATION exceptions with the Librarian.
        LaunchpadZopelessLayer.alterConnection(
                dbuser=self.dbuser,
                isolation=READ_COMMITTED_ISOLATION
                )

    def _test_display(self, text):
        """Store output from queue tool for inspection."""
        self.test_output.append(text)

    def execute_command(self, argument, queue_name='new', no_mail=True,
                        distribution_name='ubuntu',announcelist=None,
                        component_name=None, section_name=None,
                        priority_name=None, suite_name='breezy-autotest',
                        quiet=True):
        """Helper method to execute a queue command.

        Initialise output buffer and execute a command according
        given argument.

        Return the used QueueAction instance.
        """
        self.test_output = []
        queue = name_queue_map[queue_name]
        runner = CommandRunner(
            queue, distribution_name, suite_name, announcelist, no_mail,
            component_name, section_name, priority_name,
            display=self._test_display)

        return runner.execute(argument.split())

    def assertEmail(self, expected_to_addrs):
        """Pop an email from the stub queue and check its recipients."""
        from_addr, to_addrs, raw_msg = stub.test_emails.pop()
        self.assertEqual(to_addrs, expected_to_addrs)


class TestQueueTool(TestQueueBase):
    layer = LaunchpadZopelessLayer
    dbuser = config.uploadqueue.dbuser

    def setUp(self):
        """Create contents in disk for librarian sampledata."""
        # Packageupload.notify() needs real changes file data to send
        # email, so this nice simple "ed" changes file will do.  It's
        # the /wrong/ changes file for the package in the upload queue,
        # but that doesn't matter as only email addresses are parsed out
        # of it.
        changes_file_obj = open(
            datadir('ed-0.2-21/ed_0.2-21_source.changes'), 'r')
        self.test_changes_file = changes_file_obj.read()
        changes_file_obj.close()
        fillLibrarianFile(1, content=self.test_changes_file)
        TestQueueBase.setUp(self)

    def tearDown(self):
        """Remove test contents from disk."""
        cleanupLibrarianFiles()

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
        queue_size = getUtility(IPackageUploadSet).count(
            status=PackageUploadStatus.NEW,
            distroseries=bat, pocket= PackagePublishingPocket.RELEASE)
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
        queue_action = self.execute_command('accept alsa-utils', no_mail=False)
        self.assertEqual(1, queue_action.items_size)
        self.assertEqual(2, len(stub.test_emails))
        # Second email sent (first to pop from queue) is the announcement:
        self.assertEmail(['autotest_changes@ubuntu.com'])
        # First email sent (second to pop) is the uploader's notification:
        self.assertEmail(
            ['Daniel Silverstone <daniel.silverstone@canonical.com>'])

    def testAcceptingBinaryDoesntGenerateEmail(self):
        """Check if accepting a binary package does not generate email."""
        queue_action = self.execute_command(
            'accept mozilla-firefox', no_mail=False)
        self.assertEqual(1, queue_action.items_size)
        self.assertEqual(0, len(stub.test_emails))

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
            PackageUploadStatus.ACCEPTED, 'mozilla-firefox')
        self.assertQueueLength(1, breezy_autotest,
            PackageUploadStatus.ACCEPTED, 'pmount')
        self.assertQueueLength(1, breezy_autotest,
            PackageUploadStatus.ACCEPTED, 'netapplet')


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

    def testQueueDoesNotAnnounceBackports(self):
        """Check if BACKPORTS acceptance are not announced publicly.

        Queue tool normally announce acceptance in the specified changeslist
        for the distroseries in question, however BACKPORTS announce doesn't
        fit very well in that list, they cause unwanted noise.

        Further details in bug #59443
        """
        # Make breezy-autotest CURRENT in order to accept upload
        # to BACKPORTS.
        breezy_autotest = getUtility(
            IDistributionSet)['ubuntu']['breezy-autotest']
        breezy_autotest.status = DistroSeriesStatus.CURRENT

        # Store the targeted queue item for future inspection.
        # Ensure it is what we expect.
        target_queue = breezy_autotest.getQueueItems(
            status=PackageUploadStatus.UNAPPROVED,
            pocket= PackagePublishingPocket.BACKPORTS)[0]
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
        # Make breezy-autotest CURRENT in order to accept upload
        # to PROPOSED.
        breezy_autotest = getUtility(
            IDistributionSet)['ubuntu']['breezy-autotest']
        breezy_autotest.status = DistroSeriesStatus.CURRENT

        # Store the targeted queue item for future inspection.
        # Ensure it is what we expect.
        target_queue = breezy_autotest.getQueueItems(
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

        # Previously stored reference should have new state now
        self.assertEqual('ACCEPTED', target_queue.status.name)

        # No email was sent.
        self.assertEqual(0, len(stub.test_emails))

    def assertQueueLength(self, expected_length, distro_series, status, name):
        self.assertEqual(
            expected_length,
            distro_series.getQueueItems(status=status, name=name).count())

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
        breezy_autotest = getUtility(
            IDistributionSet)['ubuntu']['breezy-autotest']

        # certify we have a 'cnews' upload duplication in UNAPPROVED
        self.assertQueueLength(
            2, breezy_autotest, PackageUploadStatus.UNAPPROVED, "cnews")

        # Step 1: try to accept both
        queue_action = self.execute_command(
            'accept cnews', queue_name='unapproved',
            suite_name='breezy-autotest')

        # the first is in accepted.
        self.assertQueueLength(
            1, breezy_autotest, PackageUploadStatus.ACCEPTED, "cnews")

        # the last can't be accepted and remains in UNAPPROVED
        self.assertTrue(
            ('** cnews could not be accepted due This '
             'sourcepackagerelease is already accepted in breezy-autotest.')
            in self.test_output)
        self.assertQueueLength(
            1, breezy_autotest, PackageUploadStatus.UNAPPROVED, "cnews")

        # Step 2: try to accept the remaining item in UNAPPROVED.
        queue_action = self.execute_command(
            'accept cnews', queue_name='unapproved',
            suite_name='breezy-autotest')
        self.assertTrue(
            ('** cnews could not be accepted due This '
             'sourcepackagerelease is already accepted in breezy-autotest.')
            in self.test_output)
        self.assertQueueLength(
            1, breezy_autotest, PackageUploadStatus.UNAPPROVED, "cnews")

        # simulate a publication of the accepted item, now it is in DONE
        accepted_item = breezy_autotest.getQueueItems(
            status=PackageUploadStatus.ACCEPTED, name="cnews")[0]

        accepted_item.setDone()
        accepted_item.syncUpdate()
        self.assertQueueLength(
            1, breezy_autotest, PackageUploadStatus.DONE, "cnews")

        # Step 3: try to accept the remaining item in UNAPPROVED with the
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
            1, breezy_autotest, PackageUploadStatus.UNAPPROVED, "cnews")

        # Step 4: The only possible destiny for the remaining item it REJECT
        queue_action = self.execute_command(
            'reject cnews', queue_name='unapproved',
            suite_name='breezy-autotest')
        self.assertQueueLength(
            0, breezy_autotest, PackageUploadStatus.UNAPPROVED, "cnews")
        self.assertQueueLength(
            1, breezy_autotest, PackageUploadStatus.REJECTED, "cnews")

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

    def testRejectWithMultipleIDs(self):
        """Check if rejecting multiple items at once works.

        We can specify multiple items to reject, even mixing IDs and names.
        e.g. queue reject alsa-utils 1 3
        """
        # An additional librarian file is needed for queue item with ID 1
        # because in the sample data it points to library file alias 52.
        fillLibrarianFile(52, content=self.test_changes_file)
        breezy_autotest = getUtility(
            IDistributionSet)['ubuntu']['breezy-autotest']

        # Run the command.
        queue_action = self.execute_command('reject 1 pmount 3')

        # Test what it did.  Since all the queue items came out of the
        # NEW queue originally, the items processed should now be REJECTED.
        self.assertEqual(3, queue_action.items_size)
        self.assertQueueLength(1, breezy_autotest,
            PackageUploadStatus.REJECTED, 'mozilla-firefox')
        self.assertQueueLength(1, breezy_autotest,
            PackageUploadStatus.REJECTED, 'pmount')
        self.assertQueueLength(1, breezy_autotest,
            PackageUploadStatus.REJECTED, 'netapplet')

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
        queue_item = breezy_autotest.getQueueItems(
            status=PackageUploadStatus.NEW, name="alsa-utils")[0]
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
        # Check results.
        queue_items = list(breezy_autotest.getQueueItems(
            status=PackageUploadStatus.NEW, name='alsa-utils'))
        queue_items.extend(list(breezy_autotest.getQueueItems(
            status=PackageUploadStatus.NEW, name='netapplet')))
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
        [queue_item] = breezy_autotest.getQueueItems(
            status=PackageUploadStatus.NEW, name="alsa-utils")
        [source] = queue_item.sources
        self.assertEqual(source.sourcepackagerelease.upload_archive.purpose,
            ArchivePurpose.PARTNER)

        # Test that it changes back to primary when required.
        queue_action = self.execute_command('override source alsa-utils',
            component_name='main')
        self.assertEqual(1, queue_action.items_size)
        [queue_item] = breezy_autotest.getQueueItems(
            status=PackageUploadStatus.NEW, name="alsa-utils")
        [source] = queue_item.sources
        self.assertEqual(source.sourcepackagerelease.upload_archive.purpose,
            ArchivePurpose.PRIMARY)

    def testOverrideSourceWithNonexistentArchiveChange(self):
        """Check that overriding to a non-existent archive fails properly.

        When overriding the component, the archive may change to a
        non-existent one so ensure if fails.
        """
        ubuntu = getUtility(IDistributionSet)['ubuntu']

        LaunchpadZopelessLayer.switchDbUser("testadmin")
        proxied_archive = getUtility(IArchiveSet).getByDistroPurpose(
            ubuntu, ArchivePurpose.PARTNER)
        comm_archive = removeSecurityProxy(proxied_archive)
        comm_archive.purpose = ArchivePurpose.EMBARGOED
        LaunchpadZopelessLayer.txn.commit()
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
        [queue_item] = breezy_autotest.getQueueItems(
            status=PackageUploadStatus.NEW, name="pmount")
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
        queue_items = list(breezy_autotest.getQueueItems(
            status=PackageUploadStatus.NEW, name='pmount'))
        queue_items.extend(list(breezy_autotest.getQueueItems(
            status=PackageUploadStatus.NEW, name='mozilla-firefox')))
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

    def testOverrideBinaryWithArchiveChange(self):
        """Check if archive changes are disallowed for binary overrides.

        When overriding the component, the archive may change, so we check
        that here and make sure it's disallowed.
        """
        breezy_autotest = getUtility(
            IDistributionSet)['ubuntu']['breezy-autotest']
        # Test that it changes to partner when required.
        self.assertRaises(
            CommandRunnerError, self.execute_command, 'override binary pmount',
            component_name='partner')


class TestQueueToolInJail(TestQueueBase):
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
        cleanupLibrarianFiles()
        shutil.rmtree(self._jail)

    def _listfiles(self):
        """Return a list of files present in jail."""
        return os.listdir(self._jail)

    def _getsha1(self,filename):
        """Return a sha1 hex digest of a file"""
        file_sha = sha()
        opened_file = open(filename,"r")
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
        queue_action = self.execute_command('fetch 1')
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
        self.assertEqual(existing_sha1,new_sha1)

    def testFetchActionRaisesErrorIfDifferentFileAlreadyFetched(self):
        """Check that fetching a file that has already been fetched
        raises an error if they are not the same file.  (bug 67014)
        """
        CLOBBERED="you're clobbered"

        queue_action = self.execute_command('fetch 1')
        self.assertEqual(
            ['mozilla-firefox_0.9_i386.changes'], self._listfiles())

        # clobber the existing file, fetch it again and expect an exception
        f = open(self._listfiles()[0],"w")
        f.write(CLOBBERED)
        f.close()

        self.assertRaises(
            CommandRunnerError, self.execute_command, 'fetch 1')

        # make sure the file has not changed
        f = open(self._listfiles()[0],"r")
        line = f.read()
        f.close()

        self.assertEqual(CLOBBERED,line)

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
        fillLibrarianFile(37, FAKE_DEB_CONTENT)
        queue_action = self.execute_command('fetch pmount')

        # Check the files' names.
        files = sorted(self._listfiles())
        self.assertEqual(
            ['netapplet-1.0.0.tar.gz', 'pmount_1.9-1_all.deb'],
            files)

        # Check the files' contents.
        changes_file = open('netapplet-1.0.0.tar.gz')
        self.assertEqual(changes_file.read(), FAKE_CHANGESFILE_CONTENT)
        changes_file.close()
        debfile = open('pmount_1.9-1_all.deb')
        self.assertEqual(debfile.read(), FAKE_DEB_CONTENT)
        debfile.close()

    def testFetchMultipleItems(self):
        """Check if fetching multiple items at once works.

        We can specify multiple items to fetch, even mixing IDs and names.
        e.g. queue fetch alsa-utils 1 3
        """
        queue_action = self.execute_command('fetch 3 mozilla-firefox')
        files = self._listfiles()
        files.sort()
        self.assertEqual(
            ['mozilla-firefox_0.9_i386.changes', 'netapplet-1.0.0.tar.gz'],
            files)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

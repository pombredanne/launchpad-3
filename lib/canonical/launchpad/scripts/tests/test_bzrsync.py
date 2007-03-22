#!/usr/bin/python2.4
# Copyright (c) 2005-2006 Canonical Ltd.
# Author: Gustavo Niemeyer <gustavo@niemeyer.net>
#         David Allouche <david@allouche.net>

import datetime
import os
import shutil
import sys
import time
import unittest

from bzrlib.revision import NULL_REVISION
from bzrlib.uncommit import uncommit
from bzrlib.tests import TestCaseInTempDir, TestCaseWithTransport
import pytz
from zope.component import getUtility

from canonical.config import config
from canonical.lp import initZopeless
from canonical.lp.dbschema import (
    BranchSubscriptionDiffSize, BranchSubscriptionNotificationLevel)
from canonical.launchpad.database import (
    BranchRevision, Revision, RevisionAuthor, RevisionParent)
from canonical.launchpad.mail import stub
from canonical.launchpad.interfaces import IBranchSet, IPersonSet, IRevisionSet
from canonical.launchpad.scripts.bzrsync import BzrSync, RevisionModifiedError
from canonical.launchpad.scripts.importd.tests.helpers import (
    instrument_method, InstrumentedMethodObserver)
from canonical.launchpad.scripts.tests.webserver_helper import WebserverHelper
from canonical.testing import LaunchpadZopelessLayer


class BzrlibZopelessLayer(LaunchpadZopelessLayer):
    """Clean up the test directory created by TestCaseInTempDir tests."""

    @classmethod
    def setUp(cls):
        pass

    @classmethod
    def tearDown(cls):
        # Remove the test directory created by TestCaseInTempDir.
        # Copied from bzrlib.tests.TextTestRunner.run.
        test_root = TestCaseInTempDir.TEST_ROOT
        if test_root is not None:
            test_root = test_root.encode(sys.getfilesystemencoding())
            shutil.rmtree(test_root)


    @classmethod
    def testSetUp(cls):
        pass

    @classmethod
    def testTearDown(cls):
        pass


class BzrSyncTestCase(TestCaseWithTransport):
    """Common base for BzrSync test cases."""

    layer = BzrlibZopelessLayer

    AUTHOR = "Revision Author <author@example.com>"
    LOG = "Log message"

    def setUp(self):
        TestCaseWithTransport.setUp(self)
        self.webserver_helper = WebserverHelper()
        self.webserver_helper.setUp()
        self.setUpBzrBranch()
        LaunchpadZopelessLayer.switchDbUser(config.launchpad.dbuser)
        self.setUpDBBranch()
        LaunchpadZopelessLayer.switchDbUser(config.branchscanner.dbuser)
        self.txn = LaunchpadZopelessLayer.txn
        self.setUpAuthor()
        stub.test_emails = []
        self.bzrsync = None

    def tearDown(self):
        if self.bzrsync is not None and self.bzrsync.db_branch is not None:
            self.bzrsync.close()
        self.webserver_helper.tearDown()
        TestCaseWithTransport.tearDown(self)

    def join(self, name):
        return self.webserver_helper.join(name)

    def url(self, name):
        return self.webserver_helper.get_remote_url(name)

    def setUpBzrBranch(self):
        relpath = "bzr_branch"
        self.bzr_branch_url = self.url(relpath)
        self.bzr_tree = self.make_branch_and_tree(relpath)
        self.bzr_branch = self.bzr_tree.branch

    def setUpDBBranch(self):
        LaunchpadZopelessLayer.txn.begin()
        arbitraryownerid = 1
        self.db_branch = getUtility(IBranchSet).new(
            name="test",
            owner=arbitraryownerid,
            product=None,
            url=self.bzr_branch_url,
            title="Test branch",
            summary="Branch for testing")
        test_user = getUtility(IPersonSet).getByEmail('test@canonical.com')
        self.db_branch.subscribe(
            test_user,
            BranchSubscriptionNotificationLevel.FULL,
            BranchSubscriptionDiffSize.FIVEKLINES)
        LaunchpadZopelessLayer.txn.commit()

    def setUpAuthor(self):
        self.db_author = RevisionAuthor.selectOneBy(name=self.AUTHOR)
        if not self.db_author:
            self.txn.begin()
            self.db_author = RevisionAuthor(name=self.AUTHOR)
            self.txn.commit()

    def getCounts(self):
        return (Revision.select().count(),
                BranchRevision.select().count(),
                RevisionParent.select().count(),
                RevisionAuthor.select().count())

    def assertCounts(self, counts, new_revisions=0, new_numbers=0,
                     new_parents=0, new_authors=0):
        (old_revision_count,
         old_revisionnumber_count,
         old_revisionparent_count,
         old_revisionauthor_count) = counts
        (new_revision_count,
         new_revisionnumber_count,
         new_revisionparent_count,
         new_revisionauthor_count) = self.getCounts()
        revision_pair = (old_revision_count+new_revisions,
                         new_revision_count)
        revisionnumber_pair = (old_revisionnumber_count+new_numbers,
                               new_revisionnumber_count)
        revisionparent_pair = (old_revisionparent_count+new_parents,
                               new_revisionparent_count)
        revisionauthor_pair = (old_revisionauthor_count+new_authors,
                               new_revisionauthor_count)
        self.assertEqual(revision_pair[0], revision_pair[1],
                         "Wrong Revision count (should be %d, not %d)"
                         % revision_pair)
        self.assertEqual(revisionnumber_pair[0], revisionnumber_pair[1],
                         "Wrong BranchRevision count (should be %d, not %d)"
                         % revisionnumber_pair)
        self.assertEqual(revisionparent_pair[0], revisionparent_pair[1],
                         "Wrong RevisionParent count (should be %d, not %d)"
                         % revisionparent_pair)
        self.assertEqual(revisionauthor_pair[0], revisionauthor_pair[1],
                         "Wrong RevisionAuthor count (should be %d, not %d)"
                         % revisionauthor_pair)

    def makeBzrSync(self):
        """Create a BzrSync instance for the test branch.

        This method allow subclasses to instrument the BzrSync instance used in
        syncBranch.
        """
        self.bzrsync = BzrSync(self.txn, self.db_branch, self.bzr_branch_url)
        return self.bzrsync

    def syncBranch(self):
        """Run BzrSync on the test branch."""
        self.makeBzrSync().syncBranchAndClose()

    def syncAndCount(self, new_revisions=0, new_numbers=0,
                     new_parents=0, new_authors=0):
        """Run BzrSync and assert the number of rows added to each table."""
        counts = self.getCounts()
        self.syncBranch()
        self.assertCounts(
            counts, new_revisions=new_revisions, new_numbers=new_numbers,
            new_parents=new_parents, new_authors=new_authors)

    def writeToFile(self, filename="file", contents=None):
        """Set the contents of the specified file.

        This also adds the file to the bzr working tree if
        it isn't already there.
        """
        file = open(os.path.join(self.bzr_tree.basedir, filename), "w")
        if contents is None:
            file.write(str(time.time()+random.random()))
        else:
            file.write(contents)
        file.close()
        if not self.bzr_tree.has_filename(filename):
            self.bzr_tree.add(filename)

    def commitRevision(self, message=None, committer=None,
                       extra_parents=None, rev_id=None,
                       timestamp=None, timezone=None):
        if message is None:
            message = self.LOG
        if committer is None:
            committer = self.AUTHOR
        if extra_parents is not None:
            self.bzr_tree.add_pending_merge(*extra_parents)
        self.bzr_tree.commit(
            message, committer=committer, rev_id=rev_id,
            timestamp=timestamp, timezone=timezone, allow_pointless=True)

    def uncommitRevision(self):
        branch = self.bzr_tree.branch
        uncommit(branch, tree=self.bzr_tree)

    def makeBranchWithMerge(self):
        """Branch from bzr_tree, commit to both branches, merge the new branch
        into bzr_tree, then commit.

        :return: A list of the revisions that have been committed, as returned
        by WorkingTree.commit().
        """
        # Make the base revision.
        self.bzr_tree.commit(
            u'common parent', committer=self.AUTHOR, rev_id='r1',
            allow_pointless=True)

        # Branch from the base revision.
        new_tree = self.make_branch_and_tree('bzr_branch_merged')
        new_tree.pull(self.bzr_branch)

        # Commit to both branches
        self.bzr_tree.commit(
            u'commit one', committer=self.AUTHOR, rev_id='r2',
            allow_pointless=True)
        new_tree.commit(
            u'commit two', committer=self.AUTHOR, rev_id='r1.1.1',
            allow_pointless=True)

        # Merge and commit.
        self.bzr_tree.merge_from_branch(new_tree.branch)
        self.bzr_tree.commit(
            u'merge', committer=self.AUTHOR, rev_id='r3',
            allow_pointless=True)

    def getBranchRevisions(self):
        """Get a set summarizing the BranchRevision rows in the database.

        :return: A set of tuples (sequence, revision-id) for all the
            BranchRevisions rows belonging to self.db_branch.
        """
        return set(
            (branch_revision.sequence, branch_revision.revision.revision_id)
            for branch_revision
            in BranchRevision.selectBy(branch=self.db_branch))


class TestBzrSync(BzrSyncTestCase):

    def makeBzrSync(self):
        self.bzrsync = BzrSync(self.txn, self.db_branch, self.bzr_branch_url)
        # Load the ancestry as the database knows of it.
        self.bzrsync.retrieveDatabaseAncestry()
        # And get the history and ancestry from the branch.
        self.bzrsync.retrieveBranchDetails()
        return self.bzrsync

    def test_empty_branch(self):
        # Importing an empty branch does nothing.
        self.syncAndCount()
        self.assertEqual(self.db_branch.revision_count, 0)
        self.assertEqual(len(stub.test_emails), 0)
            
    def test_import_revision(self):
        # Importing a revision in history adds one revision and number.
        self.commitRevision()
        self.syncAndCount(new_revisions=1, new_numbers=1)
        self.assertEqual(self.db_branch.revision_count, 1)
        self.assertEqual(len(stub.test_emails), 1)
        self.failUnless('First scan of the branch detected 1 revision'
                        ' in the revision history of the=\n branch.' in
                        stub.test_emails[0][2], stub.test_emails[0][2])

    def test_import_uncommit(self):
        # Second import honours uncommit.
        self.commitRevision()
        self.syncAndCount(new_revisions=1, new_numbers=1)
        self.assertEqual(len(stub.test_emails), 1)
        self.uncommitRevision()
        self.syncAndCount(new_numbers=-1)
        self.assertEqual(self.db_branch.revision_count, 0)
        self.assertEqual(len(stub.test_emails), 2)
        self.failUnless('1 revision was removed from the branch.'
                        in stub.test_emails[1][2])

    def test_import_recommit(self):
        # Second import honours uncommit followed by commit.
        self.commitRevision('first')
        self.syncAndCount(new_revisions=1, new_numbers=1)
        self.assertEqual(self.db_branch.revision_count, 1)
        self.assertEqual(len(stub.test_emails), 1)
        self.uncommitRevision()
        self.commitRevision('second')
        self.syncAndCount(new_revisions=1)
        self.assertEqual(self.db_branch.revision_count, 1)
        [revno] = self.db_branch.revision_history
        self.assertEqual(revno.revision.log_body, 'second')
        self.assertEqual(len(stub.test_emails), 3)
        self.failUnless('1 revision was removed from the branch.'
                        in stub.test_emails[1][2])
        body = stub.test_emails[2][2]
        body_bits = [
            'revno: 1',
            'committer: Revision Author <author@example.com>',
            'branch nick: bzr_branch',
            'message:\n  second',
            'added:\n  file',
            "=3D=3D=3D added file 'file'",
            ]
        for bit in body_bits:
            self.failUnless(bit in body, '%s missing from %s' % (bit, body))

    def test_import_revision_with_url(self):
        # Importing a revision passing the url parameter works.
        self.commitRevision()
        counts = self.getCounts()
        bzrsync = BzrSync(self.txn, self.db_branch, self.bzr_branch_url)
        bzrsync.syncBranchAndClose()
        self.assertCounts(counts, new_revisions=1, new_numbers=1)

    def test_new_author(self):
        # Importing a different committer adds it as an author.
        author = "Another Author <another@example.com>"
        self.commitRevision(committer=author)
        self.syncAndCount(new_revisions=1, new_numbers=1, new_authors=1)
        db_author = RevisionAuthor.selectOneBy(name=author)
        self.assertTrue(db_author)
        self.assertEquals(db_author.name, author)

    def test_new_parent(self):
        # Importing two revisions should import a new parent.
        self.commitRevision()
        self.commitRevision()
        self.syncAndCount(new_revisions=2, new_numbers=2, new_parents=1)

    def test_shorten_history(self):
        # Commit some revisions with two paths to the head revision.
        self.commitRevision()
        merge_rev_id = self.bzr_branch.last_revision()
        self.commitRevision()
        self.commitRevision(extra_parents=[merge_rev_id])
        self.syncAndCount(new_revisions=3, new_numbers=3, new_parents=3)
        self.assertEqual(self.db_branch.revision_count, 3)

        # Sync with the shorter history.
        counts = self.getCounts()
        bzrsync = BzrSync(self.txn, self.db_branch)
        def patchedRetrieveBranchDetails():
            unpatchedRetrieveBranchDetails()
            full_history = bzrsync.bzr_history
            bzrsync.bzr_history = (full_history[:-2] + full_history[-1:])
            bzrsync.bzr_ancestry.remove(full_history[-2])
        unpatchedRetrieveBranchDetails = bzrsync.retrieveBranchDetails
        bzrsync.retrieveBranchDetails = patchedRetrieveBranchDetails
        bzrsync.syncBranchAndClose()

        # The new history is one revision shorter.
        self.assertCounts(
            counts, new_revisions=0, new_numbers=-1,
            new_parents=0, new_authors=0)
        self.assertEqual(self.db_branch.revision_count, 2)

    def test_last_scanned_id_recorded(self):
        # test that the last scanned revision ID is recorded
        self.syncAndCount()
        self.assertEquals(NULL_REVISION, self.db_branch.last_scanned_id)
        self.commitRevision()
        self.syncAndCount(new_revisions=1, new_numbers=1)
        self.assertEquals(self.bzr_branch.last_revision(),
                          self.db_branch.last_scanned_id)

    def test_timestamp_parsing(self):
        # Test that the timezone selected does not affect the
        # timestamp recorded in the database.
        self.commitRevision(rev_id='rev-1',
                            timestamp=1000000000.0, timezone=0)
        self.commitRevision(rev_id='rev-2',
                            timestamp=1000000000.0, timezone=28800)
        self.syncAndCount(new_revisions=2, new_numbers=2, new_parents=1)
        rev_1 = Revision.selectOneBy(revision_id='rev-1')
        rev_2 = Revision.selectOneBy(revision_id='rev-2')
        UTC = pytz.timezone('UTC')
        dt = datetime.datetime.fromtimestamp(1000000000.0, UTC)
        self.assertEqual(rev_1.revision_date, dt)
        self.assertEqual(rev_2.revision_date, dt)

    def assertTextEqual(self, text1, text2):
        if text1 != text2:
            # find the first point of difference
            for pos in xrange(len(text1)):
                if text1[pos] != text2[pos]:
                    raise AssertionError("Text differs at position %d\n"
                                         "  text1[%d:]: %s\n"
                                         "  text2[%d:]: %s\n"
                                         % (pos, pos, repr(text1[pos:]),
                                            pos, repr(text2[pos:])))

    def test_email_format(self):
        first_revision = 'rev-1'
        self.writeToFile(filename="hello.txt",
                         contents="Hello World\n")
        self.commitRevision(rev_id=first_revision,
                            message="Log message",
                            committer="Joe Bloggs <joe@example.com>",
                            timestamp=1000000000.0,
                            timezone=0)
        self.writeToFile(filename="hello.txt",
                         contents="Hello World\n\nFoo Bar\n")
        second_revision = 'rev-2'
        self.commitRevision(rev_id=second_revision,
                            message="Extended contents",
                            committer="Joe Bloggs <joe@example.com>",
                            timestamp=1000100000.0,
                            timezone=0)
        
        sync = BzrSync(self.txn, self.db_branch)
        try:
            revision = sync.bzr_branch.repository.get_revision(first_revision)
            diff = sync.getDiff(revision)

            expected = ("=== added file 'hello.txt'\n"
                        "--- a/hello.txt\t1970-01-01 00:00:00 +0000\n"
                        "+++ b/hello.txt\t2001-09-09 01:46:40 +0000\n@@ -0,0 +1,1 @@\n"
                        "+Hello World\n\n")
            self.assertTextEqual(diff, expected)
                             
            expected = (u"-"*60 + "\n"
                        "revno: 1\n"
                        "committer: Joe Bloggs <joe@example.com>\n"
                        "branch nick: bzr_branch\n"
                        "timestamp: Sun 2001-09-09 01:46:40 +0000\n"
                        "message:\n"
                        "  Log message\n"
                        "added:\n"
                        "  hello.txt\n")
            self.assertTextEqual(sync.getRevisionMessage(revision), expected)


            revision = sync.bzr_branch.repository.get_revision(second_revision)
            diff = sync.getDiff(revision)

            expected = ("=== modified file 'hello.txt'\n"
                        "--- a/hello.txt\t2001-09-09 01:46:40 +0000\n"
                        "+++ b/hello.txt\t2001-09-10 05:33:20 +0000\n"
                        "@@ -1,1 +1,3 @@\n"
                        " Hello World\n"
                        "+\n"
                        "+Foo Bar\n\n")
            self.assertTextEqual(diff, expected)
                             
            expected = (u"-"*60 + "\n"
                        "revno: 2\n"
                        "committer: Joe Bloggs <joe@example.com>\n"
                        "branch nick: bzr_branch\n"
                        "timestamp: Mon 2001-09-10 05:33:20 +0000\n"
                        "message:\n"
                        "  Extended contents\n"
                        "modified:\n"
                        "  hello.txt\n")
            self.assertTextEqual(sync.getRevisionMessage(revision), expected)

        finally:
            sync.close()

    def test_get_revisions_empty(self):
        # An empty branch should have no revisions.
        bzrsync = self.makeBzrSync()
        self.assertEqual([], list(bzrsync.getRevisions()))

    def test_get_revisions_linear(self):
        # If the branch has a linear ancestry, getRevisions() should yield each
        # revision along with a sequence number, starting at 1.
        self.commitRevision(rev_id=u'rev-1')
        bzrsync = self.makeBzrSync()
        self.assertEqual([(1, u'rev-1')], list(bzrsync.getRevisions()))

    def test_get_revisions_branched(self):
        # Confirm that these revisions are generated by getRevisions with None
        # as the sequence 'number'.
        self.makeBranchWithMerge()
        bzrsync = self.makeBzrSync()
        expected = set([(1, 'r1'), (2, 'r2'), (3, 'r3'), (None, 'r1.1.1')])
        self.assertEqual(expected, set(bzrsync.getRevisions()))

    def test_sync_with_merged_branches(self):
        # Confirm that when we syncHistory, all of the revisions are included
        # correctly in the BranchRevision table.
        self.makeBranchWithMerge()
        self.syncBranch()
        expected = set([(1, 'r1'), (2, 'r2'), (3, 'r3'), (None, 'r1.1.1')])
        self.assertEqual(self.getBranchRevisions(), expected)

    def test_sync_merged_to_merging(self):
        # When replacing a branch by another branch that merges it (for
        # example, as done by "bzr pull" on newer bzr releases), the database
        # must be updated appropriately.
        self.makeBranchWithMerge()
        # First, sync with the merged branch.
        self.bzr_branch_url = self.url('bzr_branch_merged')
        self.syncBranch()
        # Then sync with the merging branch.
        self.bzr_branch_url = self.url('bzr_branch')
        self.syncBranch()
        expected = set([(1, 'r1'), (2, 'r2'), (3, 'r3'), (None, 'r1.1.1')])
        self.assertEqual(self.getBranchRevisions(), expected)

    def test_sync_merging_to_merged(self):
        # When replacing a branch by one of the branches it merged, the
        # database must be updated appropriately.
        self.makeBranchWithMerge()
        # First, sync with the merging branch.
        self.bzr_branch_url = self.url('bzr_branch')
        self.syncBranch()
        # Then sync with the merged branch.
        self.bzr_branch_url = self.url('bzr_branch_merged')
        self.syncBranch()
        expected = set([(1, 'r1'), (2, 'r1.1.1')])
        self.assertEqual(self.getBranchRevisions(), expected)

    def test_retrieveBranchDetails(self):
        # retrieveBranchDetails should set last_revision, bzr_ancestry and
        # bzr_history on the BzrSync instance to match the information in the
        # Bazaar branch.
        self.makeBranchWithMerge()
        bzrsync = self.makeBzrSync()
        bzrsync.retrieveBranchDetails()
        self.assertEqual('r3', bzrsync.last_revision)
        expected_ancestry = set(['r1', 'r2', 'r1.1.1', 'r3'])
        self.assertEqual(expected_ancestry, bzrsync.bzr_ancestry)
        self.assertEqual(['r1', 'r2', 'r3'], bzrsync.bzr_history)

    def test_retrieveDatabaseAncestry(self):
        # retrieveDatabaseAncestry should set db_ancestry and db_history to
        # Launchpad's current understanding of the branch state.
        # db_branch_revision_map should map Bazaar revision_ids to
        # BranchRevision.ids.

        # Use the sampledata for this test, so we do not have to rely on
        # BzrSync to fill the database. That would cause a circular dependency,
        # as the test setup would depend on retrieveDatabaseAncestry.
        branch = getUtility(IBranchSet).getByUniqueName(
            '~name12/+junk/junk.contrib')
        self.db_branch = branch
        sampledata = list(
            BranchRevision.selectBy(branch=branch).orderBy('sequence'))
        expected_ancestry = set(branch_revision.revision.revision_id
            for branch_revision in sampledata)
        expected_history = [branch_revision.revision.revision_id
            for branch_revision in sampledata
            if branch_revision.sequence is not None]
        expected_mapping = dict(
            (branch_revision.revision.revision_id, branch_revision.id)
            for branch_revision in sampledata)

        bzrsync = self.makeBzrSync()
        bzrsync.retrieveDatabaseAncestry()
        self.assertEqual(expected_ancestry, set(bzrsync.db_ancestry))
        self.assertEqual(expected_history, list(bzrsync.db_history))
        self.assertEqual(expected_mapping, bzrsync.db_branch_revision_map)


class TestBzrSyncPerformance(BzrSyncTestCase):

    # TODO: Turn these into unit tests for planDatabaseChanges. To do this, we
    # need to change the BzrSync constructor to either delay the opening of the
    # bzr branch, so those unit-tests need not set up a dummy bzr branch.
    # -- DavidAllouche 2007-03-01

    def setUp(self):
        BzrSyncTestCase.setUp(self)
        self.clearCalls()

    def clearCalls(self):
        """Clear the record of instrumented method calls."""
        self.calls = {
            'syncRevisions': [],
            'insertBranchRevisions': [],
            'deleteBranchRevisions': []}

    def makeBzrSync(self):
        bzrsync = BzrSyncTestCase.makeBzrSync(self)
        def unary_method_called(name, args, kwargs):
            (single_arg,) = args
            self.assertEqual(kwargs, {})
            self.calls[name].append(single_arg)
        unary_observer = InstrumentedMethodObserver(called=unary_method_called)
        instrument_method(unary_observer, bzrsync, 'syncRevisions')
        instrument_method(unary_observer, bzrsync, 'deleteBranchRevisions')
        instrument_method(unary_observer, bzrsync, 'insertBranchRevisions')
        return bzrsync

    def test_no_change(self):
        # Nothing should be changed if we sync a branch that hasn't been
        # changed since the last sync
        self.makeBranchWithMerge()
        self.syncBranch()
        # Second scan has nothing to do.
        self.clearCalls()
        self.syncBranch()
        assert len(self.calls) == 3, \
               'update test for additional instrumentation'
        self.assertEqual(map(len, self.calls['syncRevisions']), [0])
        self.assertEqual(map(len, self.calls['deleteBranchRevisions']), [0])
        self.assertEqual(map(len, self.calls['insertBranchRevisions']), [0])

    def test_merged_to_merging(self):
        # When replacing a branch by another branch that merges it (for
        # example, as done by "bzr pull" on newer bzr releases), the database
        # must be updated appropriately.
        self.makeBranchWithMerge()
        # First, sync with the merged branch.
        self.bzr_branch_url = self.url('bzr_branch_merged')
        self.syncBranch()
        # Then sync with the merging branch.
        self.bzr_branch_url = self.url('bzr_branch')
        self.clearCalls()
        self.syncBranch()
        assert len(self.calls) == 3, \
               'update test for additional instrumentation'
        # Two revisions added to ancestry: r2 and r3.
        self.assertEqual(map(len, self.calls['syncRevisions']), [2])
        # One branch-revision deleted: r1.1.1, becoming a merged revision.
        self.assertEqual(map(len, self.calls['deleteBranchRevisions']), [1])
        # Three branch-revisions added: r2, r1.1.1, r3
        self.assertEqual(map(len, self.calls['insertBranchRevisions']), [3])

    def test_merging_to_merged(self):
        # When replacing a branch by one of the branches it merged, the
        # database must be updated appropriately.
        self.makeBranchWithMerge()
        # First, sync with the merging branch.
        self.bzr_branch_url = self.url('bzr_branch')
        self.syncBranch()
        # Then sync with the merged branch.
        self.bzr_branch_url = self.url('bzr_branch_merged')
        self.clearCalls()
        self.syncBranch()
        assert len(self.calls) == 3, \
               'update test for additional instrumentation'
        # No revision is added to the ancestry.
        self.assertEqual(map(len, self.calls['syncRevisions']), [0])
        # Three branch-revisions deleted: r2, r3 and r1.1.1.
        self.assertEqual(map(len, self.calls['deleteBranchRevisions']), [3])
        # One branch-revision added: r1.1.1 becoming an history revision.
        self.assertEqual(map(len, self.calls['insertBranchRevisions']), [1])

    def test_one_more_commit(self):
        # Scanning a branch which has already been scanned, and to which a
        # single simple commit was added, only do the minimal amount of work.
        self.commitRevision(rev_id='rev-1')
        # First scan checks the full ancestry, which is only one revision.
        self.syncBranch()
        # Add a single simple revision to the branch.
        self.commitRevision(rev_id='rev-2')
        # Second scan only checks the added revision.
        self.clearCalls()
        self.syncBranch()
        assert len(self.calls) == 3, \
               'update test for additional instrumentation'
        self.assertEqual(map(len, self.calls['syncRevisions']), [1])
        self.assertEqual(map(len, self.calls['deleteBranchRevisions']), [0])
        self.assertEqual(map(len, self.calls['insertBranchRevisions']), [1])


class TestBzrSyncModified(BzrSyncTestCase):

    def setUp(self):
        BzrSyncTestCase.setUp(self)
        self.bzrsync = BzrSync(self.txn, self.db_branch)

    def tearDown(self):
        self.bzrsync.close()
        BzrSyncTestCase.tearDown(self)

    def test_timestampToDatetime_with_negative_fractional(self):
        # timestampToDatetime should convert a negative, fractional timestamp
        # into a valid, sane datetime object.
        UTC = pytz.timezone('UTC')
        timestamp = -0.5
        date = self.bzrsync._timestampToDatetime(timestamp)
        self.assertEqual(
            date, datetime.datetime(1969, 12, 31, 23, 59, 59, 500000, UTC))

    def test_timestampToDatetime(self):
        # timestampTODatetime should convert a regular timestamp into a valid,
        # sane datetime object.
        UTC = pytz.timezone('UTC')
        timestamp = time.time()
        date = datetime.datetime.fromtimestamp(timestamp, tz=UTC)
        self.assertEqual(date, self.bzrsync._timestampToDatetime(timestamp))

    def test_ancient_revision(self):
        # Test that we can sync revisions with negative, fractional timestamps.

        # Make a negative, fractional timestamp and equivalent datetime
        UTC = pytz.timezone('UTC')
        old_timestamp = -0.5
        old_date = datetime.datetime(1969, 12, 31, 23, 59, 59, 500000, UTC)

        class FakeRevision:
            """A revision with a negative, fractional timestamp.
            """
            revision_id = 'rev42'
            parent_ids = ['rev1', 'rev2']
            committer = self.AUTHOR
            message = self.LOG
            timestamp = old_timestamp
            timezone = 0

        # sync the revision
        self.bzrsync.syncOneRevision(FakeRevision)

        # Find the revision we just synced and check that it has the correct
        # date.
        revision = getUtility(IRevisionSet).getByRevisionId(
            FakeRevision.revision_id)
        self.assertEqual(old_date, revision.revision_date)

    def test_revision_modified(self):
        # test that modifications to the list of parents get caught.
        class FakeRevision:
            revision_id = 'rev42'
            parent_ids = ['rev1', 'rev2']
            committer = self.AUTHOR
            message = self.LOG
            timestamp = 1000000000.0
            timezone = 0
        # synchronise the fake revision:
        counts = self.getCounts()
        self.bzrsync.syncOneRevision(FakeRevision)
        self.assertCounts(
            counts, new_revisions=1, new_numbers=0,
            new_parents=2, new_authors=0)

        # verify that synchronising the revision twice passes and does
        # not create a second revision object:
        counts = self.getCounts()
        self.bzrsync.syncOneRevision(FakeRevision)
        self.assertCounts(
            counts, new_revisions=0, new_numbers=0,
            new_parents=0, new_authors=0)

        # verify that adding a parent gets caught:
        FakeRevision.parent_ids.append('rev3')
        self.assertRaises(RevisionModifiedError,
                          self.bzrsync.syncOneRevision, FakeRevision)

        # verify that removing a parent gets caught:
        FakeRevision.parent_ids = ['rev1']
        self.assertRaises(RevisionModifiedError,
                          self.bzrsync.syncOneRevision, FakeRevision)

        # verify that reordering the parents gets caught:
        FakeRevision.parent_ids = ['rev2', 'rev1']
        self.assertRaises(RevisionModifiedError,
                          self.bzrsync.syncOneRevision, FakeRevision)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

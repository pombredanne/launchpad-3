#!/usr/bin/env python
# Copyright (c) 2005-2006 Canonical Ltd.
# Author: Gustavo Niemeyer <gustavo@niemeyer.net>
#         David Allouche <david@allouche.net>

import datetime
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
from canonical.launchpad.database import (
    BranchRevision, BugBranchRevision, Revision, RevisionAuthor,
    RevisionParent)
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestSetup
from canonical.launchpad.interfaces import (
    IBranchSet, IBugSet, IRevisionSet, NotFoundError)
from canonical.launchpad.scripts.bzrsync import BzrSync, RevisionModifiedError
from canonical.launchpad.scripts.importd.tests.helpers import (
    instrument_method, InstrumentedMethodObserver)
from canonical.launchpad.scripts.tests.webserver_helper import WebserverHelper
from canonical.launchpad.webapp import errorlog
from canonical.testing import ZopelessLayer


class BzrlibZopelessLayer(ZopelessLayer):
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
        self.zopeless_helper = LaunchpadZopelessTestSetup(
            dbuser=config.branchscanner.dbuser)
        self.zopeless_helper.setUp()
        self.txn = self.zopeless_helper.txn
        self.setUpBranch()
        self.setUpAuthor()
        self.bzrsync = None

    def tearDown(self):
        if self.bzrsync is not None and self.bzrsync.db_branch is not None:
            self.bzrsync.close()
        self.zopeless_helper.tearDown()
        self.webserver_helper.tearDown()
        TestCaseWithTransport.tearDown(self)

    def join(self, name):
        return self.webserver_helper.join(name)

    def url(self, name):
        return self.webserver_helper.get_remote_url(name)

    def makeBranch(self, relpath, name=None, owner=None, product=None,
                   title='Test branch', summary='Branch for testing'):
        return (
            self.make_branch_and_tree(relpath),
            self.makeDBBranch(relpath, name, owner, product, title, summary))

    def makeDBBranch(self, relpath, name=None, owner=None, product=None,
                   title='Test branch', summary='Branch for testing'):
        url = self.url(relpath)
        if name is None:
            name = relpath
        if owner is None:
            # Set to arbitrary owner id
            owner = 1
        self.txn.begin()
        db_branch = getUtility(IBranchSet).new(
            name=name,
            owner=owner,
            product=product,
            url=url,
            summary=summary)
        self.txn.commit()
        return db_branch

    def setUpBranch(self):
        relpath = "bzr_branch"
        self.bzr_tree, self.db_branch = self.makeBranch("bzr_branch")
        self.bzr_branch_url = self.db_branch.url
        self.bzr_branch = self.bzr_tree.branch

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

    def commitRevision(self, message=None, committer=None,
                       extra_parents=None, rev_id=None,
                       timestamp=None, timezone=None, revprops=None):
        if message is None:
            message = self.LOG
        if committer is None:
            committer = self.AUTHOR
        if extra_parents is not None:
            self.bzr_tree.add_pending_merge(*extra_parents)
        self.bzr_tree.commit(
            message, committer=committer, rev_id=rev_id,
            timestamp=timestamp, timezone=timezone, allow_pointless=True,
            revprops=revprops)

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

    def test_import_revision(self):
        # Importing a revision in history adds one revision and number.
        self.commitRevision()
        self.syncAndCount(new_revisions=1, new_numbers=1)
        self.assertEqual(self.db_branch.revision_count, 1)

    def test_import_uncommit(self):
        # Second import honours uncommit.
        self.commitRevision()
        self.syncAndCount(new_revisions=1, new_numbers=1)
        self.uncommitRevision()
        self.syncAndCount(new_numbers=-1)
        self.assertEqual(self.db_branch.revision_count, 0)

    def test_import_recommit(self):
        # Second import honours uncommit followed by commit.
        self.commitRevision('first')
        self.syncAndCount(new_revisions=1, new_numbers=1)
        self.assertEqual(self.db_branch.revision_count, 1)
        self.uncommitRevision()
        self.commitRevision('second')
        self.syncAndCount(new_revisions=1)
        self.assertEqual(self.db_branch.revision_count, 1)
        [revno] = self.db_branch.revision_history
        self.assertEqual(revno.revision.log_body, 'second')

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
            properties = {}

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
            properties = {}
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


class TestRevisionProperty(BzrSyncTestCase):
    """Tests for storting revision properties."""

    def test_revision_properties(self):
        # Revisions with properties should have records stored in the
        # RevisionProperty table, accessible through Revision.getProperties().
        self.commitRevision(rev_id='rev1', revprops={'name': 'value'})
        self.syncBranch()
        db_revision = getUtility(IRevisionSet).getByRevisionId('rev1')
        bzr_revision = self.bzr_branch.repository.get_revision('rev1')
        self.assertEquals(bzr_revision.properties, db_revision.getProperties())


class OopsLoggingTest(unittest.TestCase):
    """Test that temporarily disables the default OOPS reporting and instead
    keeps any OOPSes in a list on the instance.

    :ivar oopses: A list of oopses, [(info, request, now), ...].
    """

    def setUp(self):
        self.oopses = []
        errorlog.globalErrorUtility = self
        self._globalErrorUtility = errorlog.globalErrorUtility

    def tearDown(self):
        del self.oopses[:]
        errorlog.globalErrorUtility = self._globalErrorUtility

    def raising(self, info, request=None, now=None):
        self.oopses.append((info, request, now))


class TestBugLinking(BzrSyncTestCase, OopsLoggingTest):
    """Tests for automatic bug branch linking."""

    def setUp(self):
        BzrSyncTestCase.setUp(self)
        OopsLoggingTest.setUp(self)

    def tearDown(self):
        BzrSyncTestCase.tearDown(self)
        OopsLoggingTest.tearDown(self)

    def test_bug_branch_revision(self):
        # When we scan a revision that has the launchpad:bug property set to a
        # valid LP bug, we should create a link in the BugBranchRevision table.
        self.commitRevision(
            rev_id='rev1', revprops={'launchpad:bug': '1'})
        self.syncBranch()
        bbr = BugBranchRevision.selectOne()
        self.assertNotEqual(bbr, None)
        self.assertEqual(bbr.revision.revision_id, 'rev1')
        self.assertEqual(bbr.branch.id, self.db_branch.id)
        self.assertEqual(bbr.bug.id, 1)

    def test_bug_branch_revision_twice(self):
        # When we scan a branch twice, we should only create one link.
        self.commitRevision(
            rev_id='rev1', revprops={'launchpad:bug': '1'})
        self.syncBranch()
        self.syncBranch()
        bbrs = list(BugBranchRevision.select())
        self.assertEqual(len(bbrs), 1)

    def test_makes_bug_branch(self):
        # If no BugBranch relation exists for the branch and bug, a scan of
        # the branch should create one.
        self.commitRevision(
            rev_id='rev1', revprops={'launchpad:bug': '1'})
        self.syncBranch()
        bug = getUtility(IBugSet).get(1)
        self.assertEqual(True, bug.hasBranch(self.db_branch))

    def test_oops_on_non_existent_bug(self):
        # If the bug referred to in the revision properties doesn't actually
        # exist, then we should generate some sort of OOPS report.
        self.assertRaises(NotFoundError, getUtility(IBugSet).get, 99999)
        self.commitRevision(
            rev_id='rev1', revprops={'launchpad:bug': '99999'})
        self.syncBranch()
        self.assertEqual(len(self.oopses), 1)

    def test_oops_on_dodgy_bug(self):
        # If the revision properties provide an absurd value for the bug
        # number, we should generate an OOPS report.
        self.commitRevision(
            rev_id='rev1', revprops={'launchpad:bug': 'orange'})
        self.syncBranch()
        self.assertEqual(len(self.oopses), 1)

    def test_make_branch_and_scan_it(self):
        # Commit a revision which claims to fix a bug. If you branch from that
        # revision and then sync the new branch with Launchpad, the new branch
        # will be the one that Launchpad recognises as the bug-fixing branch.

        self.commitRevision(
            rev_id='rev1', revprops={'launchpad:bug': '1'})

        # Make a new branch and merge in our base branch.
        new_tree, new_dbbranch = self.makeBranch('branched')
        new_tree.merge_from_branch(self.bzr_branch)
        new_tree.commit(
            u'merge', committer=self.AUTHOR, rev_id='r3',
            allow_pointless=True)

        # The purpose of this test is to show what happens when revision
        # properties are not in the mainline history.
        self.failIf('rev1' in new_tree.branch.revision_history(),
                    "'rev1' in %s" % (new_tree.branch.revision_history()))

        # Sync both branches
        new_sync = BzrSync(self.txn, new_dbbranch, 'branched')
        new_sync.syncBranchAndClose()
        self.syncBranch()

        bbr = BugBranchRevision.selectOne()
        self.assertNotEqual(bbr, None)
        self.assertEqual(bbr.revision.revision_id, 'rev1')
        self.assertEqual(bbr.branch.id, new_dbbranch.id)
        self.assertEqual(bbr.bug.id, 1)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

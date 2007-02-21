#!/usr/bin/env python
# Copyright (c) 2005-2006 Canonical Ltd.
# Author: Gustavo Niemeyer <gustavo@niemeyer.net>
#         David Allouche <david@allouche.net>

import datetime
import os
import random
import time
import unittest

from bzrlib.bzrdir import BzrDir
from bzrlib.revision import NULL_REVISION
from bzrlib.uncommit import uncommit
from bzrlib.tests import TestCaseWithTransport
import pytz
from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.database import (
    Revision, BranchRevision, RevisionParent, RevisionAuthor)
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestSetup
from canonical.launchpad.interfaces import (
    IBranchSet, IRevisionSet, IBranchRevisionSet)
from canonical.launchpad.scripts.bzrsync import BzrSync, RevisionModifiedError
from canonical.launchpad.scripts.importd.tests.helpers import (
    instrument_method, InstrumentedMethodObserver)
from canonical.launchpad.scripts.tests.webserver_helper import WebserverHelper
from canonical.testing import ZopelessLayer


class BzrSyncTestCase(TestCaseWithTransport):
    """Common base for BzrSync test cases."""

    layer = ZopelessLayer

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
        self.setUpBzrBranch()
        self.setUpDBBranch()
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

    def setUpBzrBranch(self):
        self.bzr_branch_relpath = "bzr_branch"
        self.bzr_branch_abspath = self.join(self.bzr_branch_relpath)
        self.bzr_branch_url = self.url(self.bzr_branch_relpath)
        os.mkdir(self.bzr_branch_abspath)
        self.bzr_tree = BzrDir.create_standalone_workingtree(
            self.bzr_branch_abspath)
        self.bzr_branch = self.bzr_tree.branch

    def setUpDBBranch(self):
        self.txn.begin()
        arbitraryownerid = 1
        self.db_branch = getUtility(IBranchSet).new(
            name="test",
            owner=arbitraryownerid,
            product=None,
            url=self.bzr_branch_url,
            title="Test branch",
            summary="Branch for testing")
        self.txn.commit()

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
        self.makeBzrSync().syncHistoryAndClose()

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
                       timestamp=None, timezone=None):
        file = open(os.path.join(self.bzr_branch_abspath, "file"), "w")
        file.write(str(time.time()+random.random()))
        file.close()
        inventory = self.bzr_tree.read_working_inventory()
        if not inventory.has_filename("file"):
            self.bzr_tree.add("file")
        if message is None:
            message = self.LOG
        if committer is None:
            committer = self.AUTHOR
        if extra_parents is not None:
            self.bzr_tree.add_pending_merge(*extra_parents)
        self.bzr_tree.commit(message, committer=committer, rev_id=rev_id,
                             timestamp=timestamp, timezone=timezone)

    def uncommitRevision(self):
        self.bzr_tree = self.bzr_branch.bzrdir.open_workingtree()
        branch = self.bzr_tree.branch
        uncommit(branch, tree=self.bzr_tree)


class TestBzrSync(BzrSyncTestCase):

    def setUp(self):
        BzrSyncTestCase.setUp(self)
        self.bzrsync = None

    def tearDown(self):
        if self.bzrsync is not None and self.bzrsync.db_branch is not None:
            self.bzrsync.close()
        BzrSyncTestCase.tearDown(self)

    def makeBzrSync(self):
        self.bzrsync = BzrSync(self.txn, self.db_branch, self.bzr_branch_url)
        # Load the ancestry as the database knows of it.
        self.bzrsync.retrieveDatabaseAncestry()
        # And get the history and ancestry from the branch.
        self.bzrsync.retrieveBranchDetails()
        return self.bzrsync

    def syncAndCount(self, new_revisions=0, new_numbers=0,
                     new_parents=0, new_authors=0):
        counts = self.getCounts()
        self.makeBzrSync().syncHistoryAndClose()
        self.assertCounts(
            counts, new_revisions=new_revisions, new_numbers=new_numbers,
            new_parents=new_parents, new_authors=new_authors)

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
        bzrsync.syncHistoryAndClose()
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
        # commit some revisions with two paths to the head revision
        self.commitRevision()
        merge_rev_id = self.bzr_branch.last_revision()
        self.commitRevision()
        self.commitRevision(extra_parents=[merge_rev_id])
        self.syncAndCount(new_revisions=3, new_numbers=3, new_parents=3)
        self.assertEqual(self.db_branch.revision_count, 3)

        # now do a sync with a the shorter history.
        old_revision_history = self.bzr_branch.revision_history()
        new_revision_history = (old_revision_history[:-2] +
                                old_revision_history[-1:])

        counts = self.getCounts()
        bzrsync = BzrSync(self.txn, self.db_branch)
        bzrsync.retrieveDatabaseAncestry()
        bzrsync.retrieveBranchDetails()
        # now overwrite the bzr_history
        bzrsync.bzr_history = new_revision_history
        bzrsync.bzr_ancestry.remove(old_revision_history[-2])
        try:
            bzrsync.syncInitialAncestry()
            bzrsync.syncHistory()
        finally:
            bzrsync.close()

        # the new history is one revision shorter:
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
                            timestamp=1000000000.0,
                            timezone=0)
        self.commitRevision(rev_id='rev-2',
                            timestamp=1000000000.0,
                            timezone=28800)
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

    def makeBranchWithMerge(self):
        """Branch from bzr_tree, commit to both branches, merge the new branch
        into bzr_tree, then commit.

        :return: A list of the revisions that have been committed, as returned
        by WorkingTree.commit().
        """
        revisions = []

        # Make the base revision.
        revisions.append(self.bzr_tree.commit(u'common parent',
                                              committer=self.AUTHOR,
                                              allow_pointless=True))

        # Branch from the base revision.
        new_tree = self.bzr_tree.bzrdir.sprout('y').open_workingtree()

        # Commit to both branches
        revisions.append(self.bzr_tree.commit(u'commit one',
                                              committer=self.AUTHOR,
                                              allow_pointless=True))
        revisions.append(new_tree.commit(u'commit two', committer=self.AUTHOR,
                                         allow_pointless=True))

        # Merge and commit.
        self.bzr_tree.merge_from_branch(new_tree.branch)
        revisions.append(self.bzr_tree.commit(u'merge', committer=self.AUTHOR,
                                              allow_pointless=True))
        return revisions

    def test_get_revisions_branched(self):
        # Confirm that these revisions are generated by getRevisions with None
        # as the sequence 'number'.
        [rev0, rev1, rev2, rev3] = self.makeBranchWithMerge()
        bzrsync = self.makeBzrSync()
        self.assertEqual(set([(1, rev0), (2, rev1), (3, rev3), (None, rev2)]),
                         set(bzrsync.getRevisions()))

    def test_sync_with_merged_branches(self):
        # Confirm that when we syncHistory, all of the revisions are included
        # in the BranchRevision table.
        revisions = self.makeBranchWithMerge()
        bzrsync = self.makeBzrSync()
        bzrsync.syncHistoryAndClose()

        # Make a new BzrSync object, because close() renders the first one
        # unusable.
        bzrsync = self.makeBzrSync()
        bzrsync.retrieveDatabaseAncestry()
        self.assertEqual(bzrsync.db_ancestry, set(revisions))

    def test_sync_is_idempotent(self):
        # Nothing should be changed if we sync a branch that hasn't been
        # changed since the last sync
        branch_revision_set = getUtility(IBranchRevisionSet)
        revisions = self.makeBranchWithMerge()

        bzrsync = self.makeBzrSync()
        bzrsync.syncHistoryAndClose()
        ancestry = branch_revision_set.getAncestryForBranch(self.db_branch)
        ancestry1 = [(b.sequence, b.revision.revision_id) for b in ancestry]

        bzrsync = self.makeBzrSync()
        bzrsync.syncHistoryAndClose()
        ancestry = branch_revision_set.getAncestryForBranch(self.db_branch)
        ancestry2 = [(b.sequence, b.revision.revision_id) for b in ancestry]

        self.assertEqual(set(ancestry1), set(ancestry2))

    def test_retrieveBranchDetails(self):
        # retrieveBranchDetails should set last_revision, bzr_ancestry and
        # bzr_history on the BzrSync instance to match the information in the
        # Bazaar branch.
        revisions = self.makeBranchWithMerge()
        bzrsync = self.makeBzrSync()
        bzrsync.retrieveBranchDetails()

        self.assertEqual(revisions[-1], bzrsync.last_revision)
        self.assertEqual(set(revisions + [None]), set(bzrsync.bzr_ancestry))
        del revisions[-2] # Not part of the history. See makeBranchWithMerge.
        self.assertEqual(set(revisions), set(bzrsync.bzr_history))

    def test_retrieveDatabaseAncestry(self):
        # retrieveDatabaseAncestry should set db_ancestry and db_history to
        # Launchpad's current understanding of the branch state.
        # db_branch_revision_map should map Bazaar revision_ids to
        # BranchRevision.ids.

        # Put the database into a known state.
        self.makeBranchWithMerge()
        self.makeBzrSync().syncHistoryAndClose()

        bzrsync = self.makeBzrSync()
        bzrsync.retrieveDatabaseAncestry()

        b_r_set = getUtility(IBranchRevisionSet)
        ancestry = b_r_set.getAncestryForBranch(self.db_branch)
        history = b_r_set.getRevisionHistoryForBranch(self.db_branch)

        self.assertEqual(set([b.revision.revision_id for b in ancestry]),
                         bzrsync.db_ancestry)
        self.assertEqual(set([b.revision.revision_id for b in history]),
                         set(bzrsync.db_history))
        # We can't access BranchRevision.id, so just test that the keys are
        # correct.
        self.assertEqual(set([b.revision.revision_id for b in ancestry]),
                         set(bzrsync.db_branch_revision_map.keys()))


class TestBzrSyncPerformance(BzrSyncTestCase):

    def setUp(self):
        BzrSyncTestCase.setUp(self)
        self.syncrevision_calls = []

    def makeBzrSync(self):
        def syncRevision_called(name, args, kwargs):
            (bzr_revision,) = args
            self.assertEqual(kwargs, {})
            self.syncrevision_calls.append(bzr_revision.revision_id)
        bzrsync = BzrSyncTestCase.makeBzrSync(self)
        observer = InstrumentedMethodObserver(called=syncRevision_called)
        instrument_method(observer, bzrsync, 'syncRevision')
        return bzrsync

    def test_one_more_commit(self):
        # Scanning a branch which has already been scanned, and to which a
        # single simple commit was added, only runs syncRevision once, for the
        # new revision.
        self.commitRevision(rev_id='rev-1')
        # First scan checks the full ancestry, which is only one revision.
        self.syncBranch()
        self.assertEqual(self.syncrevision_calls, ['rev-1'])
        # Add a single simple revision to the branch.
        self.commitRevision(rev_id='rev-2')
        # Second scan only checks the added revision.
        self.syncrevision_calls = []
        self.syncBranch()
        self.assertEqual(self.syncrevision_calls, ['rev-2'])


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
        self.bzrsync.syncRevision(FakeRevision)

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
        self.bzrsync.syncRevision(FakeRevision)
        self.assertCounts(
            counts, new_revisions=1, new_numbers=0,
            new_parents=2, new_authors=0)

        # verify that synchronising the revision twice passes and does
        # not create a second revision object:
        counts = self.getCounts()
        self.bzrsync.syncRevision(FakeRevision)
        self.assertCounts(
            counts, new_revisions=0, new_numbers=0,
            new_parents=0, new_authors=0)

        # verify that adding a parent gets caught:
        FakeRevision.parent_ids.append('rev3')
        self.assertRaises(RevisionModifiedError,
                          self.bzrsync.syncRevision, FakeRevision)

        # verify that removing a parent gets caught:
        FakeRevision.parent_ids = ['rev1']
        self.assertRaises(RevisionModifiedError,
                          self.bzrsync.syncRevision, FakeRevision)

        # verify that reordering the parents gets caught:
        FakeRevision.parent_ids = ['rev2', 'rev1']
        self.assertRaises(RevisionModifiedError,
                          self.bzrsync.syncRevision, FakeRevision)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

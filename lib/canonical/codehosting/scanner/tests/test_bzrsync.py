#!/usr/bin/python2.4
# Copyright (c) 2005-2009 Canonical Ltd.
# pylint: disable-msg=W0141

import datetime
import os
import random
import time
import transaction
import unittest

from bzrlib.revision import NULL_REVISION, Revision as BzrRevision
from bzrlib.transport import (
    get_transport, register_transport, unregister_transport)
from bzrlib.transport.chroot import ChrootServer
from bzrlib.uncommit import uncommit
from bzrlib.tests import TestCaseWithTransport
import pytz
from twisted.python.util import mergeFunctionMetadata
from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.database import (
    BranchRevision, Revision, RevisionAuthor, RevisionParent)
from canonical.launchpad.interfaces import IRevisionSet
from canonical.launchpad.interfaces.branch import IBranchSet
from canonical.launchpad.interfaces.branchjob import IRosettaUploadJobSource
from canonical.launchpad.interfaces.translations import (
    TranslationsBranchImportMode)
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.codehosting.scanner.bzrsync import (
    BzrSync, InvalidStackedBranchURL)
from canonical.codehosting.bzrutils import ensure_base
from canonical.testing import LaunchpadZopelessLayer


def run_as_db_user(username):
    """Create a decorator that will run a function as the given database user.
    """
    def _run_with_different_user(f):
        def decorated(*args, **kwargs):
            current_user = LaunchpadZopelessLayer.txn._dbuser
            if current_user == username:
                return f(*args, **kwargs)
            LaunchpadZopelessLayer.switchDbUser(username)
            try:
                return f(*args, **kwargs)
            finally:
                LaunchpadZopelessLayer.switchDbUser(current_user)
        return mergeFunctionMetadata(f, decorated)
    return _run_with_different_user


class FakeTransportServer:
    """Set up a fake transport at a given URL prefix.

    For testing purposes.
    """

    def __init__(self, transport, url_prefix='lp-mirrored:///'):
        """Constructor.

        :param transport: The backing transport to store the data with.
        :param url_prefix: The URL prefix to access this transport.
        """
        self._transport = transport
        self._url_prefix = url_prefix
        self._chroot_server = None

    def setUp(self):
        """Activate the transport URL."""
        # The scanner tests assume that branches live on a Launchpad virtual
        # filesystem rooted at 'lp-mirrored:///'. Rather than provide the
        # entire virtual filesystem here, we fake it by having a chrooted
        # transport do the work.
        register_transport(self._url_prefix, self._transportFactory)
        self._chroot_server = ChrootServer(self._transport)
        self._chroot_server.setUp()

    def tearDown(self):
        """Deactivate the transport URL."""
        self._chroot_server.tearDown()
        unregister_transport(self._url_prefix, self._transportFactory)

    def _transportFactory(self, url):
        assert url.startswith(self._url_prefix)
        url = self._chroot_server.get_url() + url[len(self._url_prefix):]
        return get_transport(url)


class BzrSyncTestCase(TestCaseWithTransport):
    """Common base for BzrSync test cases."""

    layer = LaunchpadZopelessLayer

    LOG = "Log message"

    def setUp(self):
        TestCaseWithTransport.setUp(self)
        self.factory = LaunchpadObjectFactory()
        self.makeFixtures()
        self.lp_db_user = config.launchpad.dbuser
        LaunchpadZopelessLayer.switchDbUser(config.branchscanner.dbuser)
        # The lp-mirrored transport is set up by the branch_scanner module.
        # Here we set up a fake so that we can test without worrying about
        # authservers and the like.
        server = FakeTransportServer(self.get_transport())
        server.setUp()
        self.addCleanup(server.tearDown)

    def makeFixtures(self):
        """Makes test fixtures before we switch to the scanner db user."""
        self.db_branch = self.makeDatabaseBranch()
        self.bzr_tree = self.makeBzrBranchAndTree(self.db_branch)
        self.bzr_branch = self.bzr_tree.branch

    def syncBazaarBranchToDatabase(self, bzr_branch, db_branch):
        """Sync `bzr_branch` into the database as `db_branch`."""
        syncer = self.makeBzrSync(db_branch)
        syncer.syncBranchAndClose(bzr_branch)

    def makeBzrBranchAndTree(self, db_branch, format=None):
        """Make a Bazaar branch at the warehouse location of `db_branch`."""
        ensure_base(self.get_transport(db_branch.unique_name))
        return self.make_branch_and_tree(db_branch.unique_name, format=format)

    def makeDatabaseBranch(self, *args, **kwargs):
        """Make an arbitrary branch in the database."""
        LaunchpadZopelessLayer.txn.begin()
        new_branch = self.factory.makeAnyBranch(*args, **kwargs)
        # Unsubscribe the implicit owner subscription.
        new_branch.unsubscribe(new_branch.owner)
        LaunchpadZopelessLayer.txn.commit()
        return new_branch

    def getCounts(self):
        """Return the number of rows in core revision-related tables.

        :return: (num_revisions, num_branch_revisions, num_revision_parents,
            num_revision_authors)
        """
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
        self.assertEqual(
            new_revisions,
            new_revision_count - old_revision_count,
            "Wrong number of new database Revisions.")
        self.assertEqual(
            new_numbers,
            new_revisionnumber_count - old_revisionnumber_count,
            "Wrong number of new BranchRevisions.")
        self.assertEqual(
            new_parents,
            new_revisionparent_count - old_revisionparent_count,
            "Wrong number of new RevisionParents.")
        self.assertEqual(
            new_authors,
            new_revisionauthor_count - old_revisionauthor_count,
            "Wrong number of new RevisionAuthors.")

    def makeBzrSync(self, db_branch):
        """Create a BzrSync instance for the test branch.

        This method allow subclasses to instrument the BzrSync instance used
        in syncBranch.
        """
        return BzrSync(LaunchpadZopelessLayer.txn, db_branch)

    def syncAndCount(self, db_branch=None, new_revisions=0, new_numbers=0,
                     new_parents=0, new_authors=0):
        """Run BzrSync and assert the number of rows added to each table."""
        if db_branch is None:
            db_branch = self.db_branch
        counts = self.getCounts()
        self.makeBzrSync(db_branch).syncBranchAndClose()
        self.assertCounts(
            counts, new_revisions=new_revisions, new_numbers=new_numbers,
            new_parents=new_parents, new_authors=new_authors)

    def commitRevision(self, message=None, committer=None,
                       extra_parents=None, rev_id=None,
                       timestamp=None, timezone=None, revprops=None):
        if message is None:
            message = self.LOG
        if committer is None:
            committer = self.factory.getUniqueString()
        if extra_parents is not None:
            self.bzr_tree.add_pending_merge(*extra_parents)
        return self.bzr_tree.commit(
            message, committer=committer, rev_id=rev_id,
            timestamp=timestamp, timezone=timezone, allow_pointless=True,
            revprops=revprops)

    def uncommitRevision(self):
        branch = self.bzr_tree.branch
        uncommit(branch, tree=self.bzr_tree)

    def makeBranchWithMerge(self, base_rev_id, trunk_rev_id, branch_rev_id,
                            merge_rev_id):
        """Make a branch that has had another branch merged into it.

        Creates two Bazaar branches and two database branches associated with
        them. The first branch has three commits: the base revision, the
        'trunk' revision and the 'merged' revision.

        The second branch is branched from the base revision, has the 'branch'
        revision committed to it and is then merged into the first branch.

        Or, in other words::

               merge
                 |  \
                 |   \
                 |    \
               trunk   branch
                 |    /
                 |   /
                 |  /
                base

        :param base_rev_id: The revision ID of the initial commit.
        :param trunk_rev_id: The revision ID of the mainline commit.
        :param branch_rev_id: The revision ID of the revision committed to
            the branch that is merged into the mainline.
        :param merge_rev_id: The revision ID of the revision that merges the
            branch into the mainline branch.
        :return: (db_trunk, trunk_tree), (db_branch, branch_tree).
        """

        LaunchpadZopelessLayer.switchDbUser(self.lp_db_user)

        # Make the base revision.
        db_branch = self.makeDatabaseBranch()
        trunk_tree = self.makeBzrBranchAndTree(db_branch)
        trunk_tree.commit(u'base revision', rev_id=base_rev_id)

        # Branch from the base revision.
        new_db_branch = self.makeDatabaseBranch(product=db_branch.product)
        branch_tree = self.makeBzrBranchAndTree(new_db_branch)
        branch_tree.pull(trunk_tree.branch)

        # Commit to both branches.
        trunk_tree.commit(u'trunk revision', rev_id=trunk_rev_id)
        branch_tree.commit(u'branch revision', rev_id=branch_rev_id)

        # Merge branch into trunk.
        trunk_tree.merge_from_branch(branch_tree.branch)
        trunk_tree.commit(u'merge revision', rev_id=merge_rev_id)

        LaunchpadZopelessLayer.txn.commit()
        LaunchpadZopelessLayer.switchDbUser(config.branchscanner.dbuser)

        return (db_branch, trunk_tree), (new_db_branch, branch_tree)

    def getBranchRevisions(self, db_branch):
        """Get a set summarizing the BranchRevision rows in the database.

        :return: A set of tuples (sequence, revision-id) for all the
            BranchRevisions rows belonging to self.db_branch.
        """
        return set(
            (branch_revision.sequence, branch_revision.revision.revision_id)
            for branch_revision
            in BranchRevision.selectBy(branch=db_branch))

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
        self.bzr_tree.lock_write()
        try:
            inventory = self.bzr_tree.read_working_inventory()
            if not inventory.has_filename(filename):
                self.bzr_tree.add(filename)
        finally:
            self.bzr_tree.unlock()


class TestBzrSync(BzrSyncTestCase):

    def isMainline(self, db_branch, revision_id):
        """Is `revision_id` in the mainline history of `db_branch`?"""
        for branch_revision in db_branch.revision_history:
            if branch_revision.revision.revision_id == revision_id:
                return True
        return False

    def assertInMainline(self, revision_id, db_branch):
        """Assert that `revision_id` is in the mainline of `db_branch`."""
        self.failUnless(
            self.isMainline(db_branch, revision_id),
            "%r not in mainline of %r" % (revision_id, db_branch))

    def assertNotInMainline(self, revision_id, db_branch):
        """Assert that `revision_id` is not in the mainline of `db_branch`."""
        self.failIf(
            self.isMainline(db_branch, revision_id),
            "%r in mainline of %r" % (revision_id, db_branch))

    def test_empty_branch(self):
        # Importing an empty branch does nothing.
        self.syncAndCount()
        self.assertEqual(self.db_branch.revision_count, 0)

    def test_import_revision(self):
        # Importing a revision in history adds one revision and number.
        self.commitRevision()
        self.syncAndCount(new_revisions=1, new_numbers=1, new_authors=1)
        self.assertEqual(self.db_branch.revision_count, 1)

    def test_import_uncommit(self):
        # Second import honours uncommit.
        self.commitRevision()
        self.syncAndCount(new_revisions=1, new_numbers=1, new_authors=1)
        self.uncommitRevision()
        self.syncAndCount(new_numbers=-1)
        self.assertEqual(self.db_branch.revision_count, 0)

    def test_import_recommit(self):
        # Second import honours uncommit followed by commit.
        # When scanning the uncommit and new commit
        # there should be an email generated saying that
        # 1 (in this case) revision has been removed,
        # and another email with the diff and log message.
        self.commitRevision('first')
        self.syncAndCount(new_revisions=1, new_numbers=1, new_authors=1)
        self.assertEqual(self.db_branch.revision_count, 1)
        self.uncommitRevision()
        self.commitRevision('second')
        self.syncAndCount(new_revisions=1, new_authors=1)
        self.assertEqual(self.db_branch.revision_count, 1)
        [revno] = self.db_branch.revision_history
        self.assertEqual(revno.revision.log_body, 'second')

    def test_import_revision_with_url(self):
        # Importing a revision passing the url parameter works.
        self.commitRevision()
        counts = self.getCounts()
        bzrsync = BzrSync(LaunchpadZopelessLayer.txn, self.db_branch)
        bzrsync.syncBranchAndClose()
        self.assertCounts(
            counts, new_revisions=1, new_numbers=1, new_authors=1)

    def test_new_author(self):
        # Importing a different committer adds it as an author.
        author = "Another Author <another@example.com>"
        self.commitRevision(committer=author)
        self.syncAndCount(new_revisions=1, new_numbers=1, new_authors=1)
        db_author = RevisionAuthor.selectOneBy(name=author)
        self.assertEquals(db_author.name, author)

    def test_new_parent(self):
        # Importing two revisions should import a new parent.
        self.commitRevision()
        self.commitRevision()
        self.syncAndCount(
            new_revisions=2, new_numbers=2, new_parents=1, new_authors=2)

    def test_sync_updates_branch(self):
        # test that the last scanned revision ID is recorded
        self.syncAndCount()
        self.assertEquals(NULL_REVISION, self.db_branch.last_scanned_id)
        last_modified = self.db_branch.date_last_modified
        last_scanned = self.db_branch.last_scanned
        self.commitRevision()
        self.syncAndCount(new_revisions=1, new_numbers=1, new_authors=1)
        self.assertEquals(self.bzr_branch.last_revision(),
                          self.db_branch.last_scanned_id)
        self.assertTrue(self.db_branch.last_scanned > last_scanned,
                        "last_scanned was not updated")
        self.assertTrue(self.db_branch.date_last_modified > last_modified,
                        "date_last_modifed was not updated")

    def test_timestamp_parsing(self):
        # Test that the timezone selected does not affect the
        # timestamp recorded in the database.
        self.commitRevision(rev_id='rev-1',
                            timestamp=1000000000.0, timezone=0)
        self.commitRevision(rev_id='rev-2',
                            timestamp=1000000000.0, timezone=28800)
        self.syncAndCount(
            new_revisions=2, new_numbers=2, new_parents=1, new_authors=2)
        rev_1 = Revision.selectOneBy(revision_id='rev-1')
        rev_2 = Revision.selectOneBy(revision_id='rev-2')
        UTC = pytz.timezone('UTC')
        dt = datetime.datetime.fromtimestamp(1000000000.0, UTC)
        self.assertEqual(rev_1.revision_date, dt)
        self.assertEqual(rev_2.revision_date, dt)

    def test_get_revisions_empty(self):
        # An empty branch should have no revisions.
        bzrsync = self.makeBzrSync(self.db_branch)
        bzr_ancestry, bzr_history = (
            bzrsync.retrieveBranchDetails(self.bzr_branch))
        self.assertEqual(
            [], list(bzrsync.getRevisions(bzr_history, bzr_ancestry)))

    def test_get_revisions_linear(self):
        # If the branch has a linear ancestry, getRevisions() should yield
        # each revision along with a sequence number, starting at 1.
        self.commitRevision(rev_id='rev-1')
        bzrsync = self.makeBzrSync(self.db_branch)
        bzr_ancestry, bzr_history = (
            bzrsync.retrieveBranchDetails(self.bzr_branch))
        self.assertEqual(
            [('rev-1', 1)],
            list(bzrsync.getRevisions(bzr_history, bzr_ancestry)))

    def test_get_revisions_branched(self):
        # Confirm that these revisions are generated by getRevisions with None
        # as the sequence 'number'.
        (db_branch, bzr_tree), ignored = self.makeBranchWithMerge(
            'base', 'trunk', 'branch', 'merge')
        bzrsync = self.makeBzrSync(db_branch)
        bzr_ancestry, bzr_history = (
            bzrsync.retrieveBranchDetails(bzr_tree.branch))
        expected = set(
            [('base', 1), ('trunk', 2), ('merge', 3), ('branch', None)])
        self.assertEqual(
            expected, set(bzrsync.getRevisions(bzr_history, bzr_ancestry)))

    def test_sync_with_merged_branches(self):
        # Confirm that when we syncHistory, all of the revisions are included
        # correctly in the BranchRevision table.
        (db_branch, branch_tree), ignored = self.makeBranchWithMerge(
            'r1', 'r2', 'r1.1.1', 'r3')
        self.makeBzrSync(db_branch).syncBranchAndClose()
        expected = set(
            [(1, 'r1'), (2, 'r2'), (3, 'r3'), (None, 'r1.1.1')])
        self.assertEqual(self.getBranchRevisions(db_branch), expected)

    def test_sync_merged_to_merging(self):
        # A revision's sequence in the BranchRevision table will change from
        # not NULL to NULL if that revision changes from mainline to not
        # mainline when synced.

        (db_trunk, trunk_tree), (db_branch, branch_tree) = (
            self.makeBranchWithMerge('base', 'trunk', 'branch', 'merge'))

        self.syncBazaarBranchToDatabase(trunk_tree.branch, db_branch)
        self.assertInMainline('trunk', db_branch)

        self.syncBazaarBranchToDatabase(branch_tree.branch, db_branch)
        self.assertNotInMainline('trunk', db_branch)
        self.assertInMainline('branch', db_branch)

    def test_sync_merging_to_merged(self):
        # When replacing a branch by one of the branches it merged, the
        # database must be updated appropriately.
        (db_trunk, trunk_tree), (db_branch, branch_tree) = (
            self.makeBranchWithMerge('base', 'trunk', 'branch', 'merge'))
        # First, sync with the merging branch.
        self.syncBazaarBranchToDatabase(trunk_tree.branch, db_trunk)
        # Then sync with the merged branch.
        self.syncBazaarBranchToDatabase(branch_tree.branch, db_trunk)
        expected = set([(1, 'base'), (2, 'branch')])
        self.assertEqual(self.getBranchRevisions(db_trunk), expected)

    def test_retrieveBranchDetails(self):
        # retrieveBranchDetails should set last_revision, bzr_ancestry and
        # bzr_history on the BzrSync instance to match the information in the
        # Bazaar branch.
        (db_trunk, trunk_tree), ignored = self.makeBranchWithMerge(
            'base', 'trunk', 'branch', 'merge')
        bzrsync = self.makeBzrSync(db_trunk)
        bzr_ancestry, bzr_history = (
            bzrsync.retrieveBranchDetails(trunk_tree.branch))
        expected_ancestry = set(['base', 'trunk', 'branch', 'merge'])
        self.assertEqual(expected_ancestry, bzr_ancestry)
        self.assertEqual(['base', 'trunk', 'merge'], bzr_history)

    def test_retrieveDatabaseAncestry(self):
        # retrieveDatabaseAncestry should set db_ancestry and db_history to
        # Launchpad's current understanding of the branch state.
        # db_branch_revision_map should map Bazaar revision_ids to
        # BranchRevision.ids.

        # Use the sampledata for this test, so we do not have to rely on
        # BzrSync to fill the database. That would cause a circular
        # dependency, as the test setup would depend on
        # retrieveDatabaseAncestry.
        branch = getUtility(IBranchSet).getByUniqueName(
            '~name12/+junk/junk.contrib')
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

        self.makeBzrBranchAndTree(branch)

        bzrsync = self.makeBzrSync(branch)
        db_ancestry, db_history, db_branch_revision_map = (
            bzrsync.retrieveDatabaseAncestry())
        self.assertEqual(expected_ancestry, set(db_ancestry))
        self.assertEqual(expected_history, list(db_history))
        self.assertEqual(expected_mapping, db_branch_revision_map)


class TestScanStackedBranches(BzrSyncTestCase):
    """Tests for scanning stacked branches."""

    @run_as_db_user(config.launchpad.dbuser)
    def testStackedBranchBadURL(self):
        # The scanner will raise an InvalidStackedBranchURL when it tries to
        # open a branch stacked on a non- lp-mirrored:// schema.
        db_branch = self.makeDatabaseBranch()
        stacked_on_branch = self.make_branch('stacked-on', format='1.6')
        self.assertFalse(stacked_on_branch.base.startswith('lp-mirrored://'))
        bzr_tree = self.makeBzrBranchAndTree(db_branch, format='1.6')
        bzr_tree.branch.set_stacked_on_url(stacked_on_branch.base)
        scanner = self.makeBzrSync(db_branch)
        self.assertRaises(InvalidStackedBranchURL, scanner.syncBranchAndClose)

    @run_as_db_user(config.launchpad.dbuser)
    def testStackedBranch(self):
        # We can scan a stacked branch that's stacked on a branch that has an
        # lp-mirrored:// URL.
        db_stacked_on_branch = self.factory.makeAnyBranch()
        stacked_on_tree = self.makeBzrBranchAndTree(
            db_stacked_on_branch, format='1.6')
        db_stacked_branch = self.factory.makeAnyBranch()
        stacked_tree = self.makeBzrBranchAndTree(
            db_stacked_branch, format='1.6')
        stacked_tree.branch.set_stacked_on_url(
            'lp-mirrored:///%s' % db_stacked_on_branch.unique_name)
        scanner = self.makeBzrSync(db_stacked_branch)
        # This does not raise an exception.
        scanner.syncBranchAndClose()


class TestBzrSyncOneRevision(BzrSyncTestCase):
    """Tests for `BzrSync.syncOneRevision`."""

    def setUp(self):
        BzrSyncTestCase.setUp(self)
        self.bzrsync = self.makeBzrSync(self.db_branch)

    def test_ancient_revision(self):
        # Test that we can sync revisions with negative, fractional
        # timestamps.

        # Make a negative, fractional timestamp and equivalent datetime
        UTC = pytz.timezone('UTC')
        old_timestamp = -0.5
        old_date = datetime.datetime(1969, 12, 31, 23, 59, 59, 500000, UTC)

        # Fake revision with negative timestamp.
        fake_rev = BzrRevision(
            revision_id='rev42', parent_ids=['rev1', 'rev2'],
            committer=self.factory.getUniqueString(), message=self.LOG,
            timestamp=old_timestamp, timezone=0, properties={})

        # Sync the revision.  The second parameter is a dict of revision ids
        # to revnos, and will error if the revision id is not in the dict.
        self.bzrsync.syncOneRevision(fake_rev, {'rev42': None})

        # Find the revision we just synced and check that it has the correct
        # date.
        revision = getUtility(IRevisionSet).getByRevisionId(
            fake_rev.revision_id)
        self.assertEqual(old_date, revision.revision_date)


class TestBzrTranslationsUploadJob(BzrSyncTestCase):
    """Tests BzrSync support for generating TranslationsUploadJobs."""

    def setUp(self):
        BzrSyncTestCase.setUp(self)

    def _makeProductSeries(self, mode = None):
        """Switch to the Launchpad db user to create and configure a
        product series that is linked to the the branch.
        """
        try:
            LaunchpadZopelessLayer.switchDbUser(self.lp_db_user)
            self.product_series = self.factory.makeProductSeries()
            self.product_series.branch = self.db_branch
            if mode is not None:
                self.product_series.translations_autoimport_mode = mode
            transaction.commit()
        finally:
            LaunchpadZopelessLayer.switchDbUser(config.branchscanner.dbuser)

    def test_upload_on_new_revision_no_series(self):
        # Syncing a branch with a changed tip does not create a
        # new RosettaUploadJob if no series is linked to this branch.
        self.commitRevision()
        self.makeBzrSync(self.db_branch).syncBranchAndClose()
        ready_jobs = list(getUtility(IRosettaUploadJobSource).iterReady())
        self.assertEqual([], ready_jobs)

    def test_upload_on_new_revision_series_not_configured(self):
        # Syncing a branch with a changed tip does not create a
        # new RosettaUploadJob if the linked product series is not 
        # configured for translation uploads.
        self._makeProductSeries()
        self.commitRevision()
        self.makeBzrSync(self.db_branch).syncBranchAndClose()
        ready_jobs = list(getUtility(IRosettaUploadJobSource).iterReady())
        self.assertEqual([], ready_jobs)

    def test_upload_on_new_revision(self):
        # Syncing a branch with a changed tip creates a new RosettaUploadJob.
        self._makeProductSeries(
            TranslationsBranchImportMode.IMPORT_TEMPLATES)
        revision_id = self.commitRevision()
        self.makeBzrSync(self.db_branch).syncBranchAndClose()
        self.db_branch.last_mirrored_id = revision_id
        self.db_branch.last_scanned_id = revision_id
        ready_jobs = list(getUtility(IRosettaUploadJobSource).iterReady())
        self.assertEqual(1, len(ready_jobs))
        job = ready_jobs[0]
        # The right job will have our branch.
        self.assertEqual(self.db_branch, job.branch)


class TestRevisionProperty(BzrSyncTestCase):
    """Tests for storting revision properties."""

    def test_revision_properties(self):
        # Revisions with properties should have records stored in the
        # RevisionProperty table, accessible through Revision.getProperties().
        properties = {'name': 'value'}
        self.commitRevision(rev_id='rev1', revprops=properties)
        self.makeBzrSync(self.db_branch).syncBranchAndClose()
        # Check that properties were saved to the revision.
        bzr_revision = self.bzr_branch.repository.get_revision('rev1')
        self.assertEquals(properties, bzr_revision.properties)
        # Check that properties are stored in the database.
        db_revision = getUtility(IRevisionSet).getByRevisionId('rev1')
        self.assertEquals(properties, db_revision.getProperties())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

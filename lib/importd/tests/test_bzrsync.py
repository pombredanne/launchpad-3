#!/usr/bin/env python
# Copyright (c) 2005 Canonical Ltd.
# Author: Gustavo Niemeyer <gustavo@niemeyer.net>
#         David Allouche <david@allouche.net>

import logging
import random
import time
import os

from bzrlib.branch import Branch as BzrBranch

from canonical.launchpad.database import (
    Branch, Revision, RevisionNumber, RevisionParent, RevisionAuthor)

from importd.bzrsync import BzrSync
from importd.tests import helpers, TestUtil

# Boilerplate to get getUtility(ILaunchpadCelebrities) working in BzrSync.
from canonical.launchpad.interfaces import (
    ILaunchpadCelebrities, IPersonSet, IBranchSet)
from canonical.launchpad.utilities import LaunchpadCelebrities
from canonical.launchpad.database import PersonSet, BranchSet
from zope.app.tests.placelesssetup import setUp as zopePlacelessSetUp
from zope.app.tests.placelesssetup import tearDown as zopePlacelessTearDown
from zope.app.tests import ztapi


class TestBzrSync(helpers.WebserverTestCase):

    AUTHOR = "Revision Author <author@example.com>"
    LOG = "Log message"

    def setUp(self):
        helpers.WebserverTestCase.setUp(self)
        self.trans_manager = self.zopeless_helper.txn
        self.setUpBzrBranch()
        self.setUpDBBranch()
        self.setUpAuthor()

        # Boilerplate to get getUtility(ILaunchpadCelebrities) working
        # inside BzrSync.
        zopePlacelessSetUp()
        ztapi.provideUtility(ILaunchpadCelebrities, LaunchpadCelebrities())
        ztapi.provideUtility(IPersonSet, PersonSet())
        ztapi.provideUtility(IBranchSet, BranchSet())

    def tearDown(self):
        zopePlacelessTearDown()
        helpers.WebserverTestCase.tearDown(self)

    def setUpBzrBranch(self):
        self.bzr_branch_relpath = "bzr_branch"
        self.bzr_branch_abspath = self.path(self.bzr_branch_relpath)
        self.bzr_branch_url = self.url(self.bzr_branch_relpath)
        os.mkdir(self.bzr_branch_abspath)
        self.bzr_branch = BzrBranch.initialize(self.bzr_branch_abspath)

    def setUpDBBranch(self):
        self.trans_manager.begin()
        randomownerid = 1
        self.db_branch = Branch(name="test",
                                url=self.bzr_branch_url,
                                home_page=None,
                                title="Test branch",
                                summary="Branch for testing",
                                product=None,
                                owner=randomownerid)
        self.trans_manager.commit()

    def setUpAuthor(self):
        self.db_author = RevisionAuthor.selectOneBy(name=self.AUTHOR)
        if not self.db_author:
            self.trans_manager.begin()
            self.db_author = RevisionAuthor(name=self.AUTHOR)
            self.trans_manager.commit()

    def getCounts(self):
        return (Revision.select().count(),
                RevisionNumber.select().count(),
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
                         "Wrong RevisionNumber count (should be %d, not %d)"
                         % revisionnumber_pair)
        self.assertEqual(revisionparent_pair[0], revisionparent_pair[1],
                         "Wrong RevisionParent count (should be %d, not %d)"
                         % revisionparent_pair)
        self.assertEqual(revisionauthor_pair[0], revisionauthor_pair[1],
                         "Wrong RevisionAuthor count (should be %d, not %d)"
                         % revisionauthor_pair)

    def commitRevision(self, message=None, committer=None):
        file = open(os.path.join(self.bzr_branch_abspath, "file"), "w")
        file.write(str(time.time()+random.random()))
        file.close()
        inventory = self.bzr_branch.read_working_inventory()
        if not inventory.has_filename("file"):
            self.bzr_branch.add("file")
        if message is None:
            message = self.LOG
        if committer is None:
            committer = self.AUTHOR
        self.bzr_branch.commit(message, committer=committer)

    def test_empty_branch(self):
        """Importing an empty branch does nothing."""
        counts = self.getCounts()
        BzrSync(self.trans_manager, self.db_branch.id).syncHistory()
        self.assertCounts(counts)

    def test_import_revision(self):
        """Importing a revision in history adds one revision and number."""
        self.commitRevision()
        counts = self.getCounts()
        BzrSync(self.trans_manager, self.db_branch.id).syncHistory()
        self.assertCounts(counts, new_revisions=1, new_numbers=1)

    def test_import_revision_with_url(self):
        """Importing a revision passing the url parameter works."""
        self.commitRevision()
        counts = self.getCounts()
        bzrsync = BzrSync(self.trans_manager, self.db_branch.id,
                          self.bzr_branch_url)
        bzrsync.syncHistory()
        self.assertCounts(counts, new_revisions=1, new_numbers=1)

    def test_new_author(self):
        """Importing a different committer adds it as an author."""
        author = "Another Author <another@example.com>"
        self.commitRevision(committer=author)
        counts = self.getCounts()
        BzrSync(self.trans_manager, self.db_branch.id).syncHistory()
        self.assertCounts(counts, new_revisions=1, new_numbers=1,
                          new_authors=1)
        db_author = RevisionAuthor.selectOneBy(name=author)
        self.assertTrue(db_author)
        self.assertEquals(db_author.name, author)

    def test_new_parent(self):
        """Importing two revisions should import a new parent."""
        self.commitRevision()
        self.commitRevision()
        counts = self.getCounts()
        BzrSync(self.trans_manager, self.db_branch.id).syncHistory()
        self.assertCounts(counts, new_revisions=2, new_numbers=2,
                          new_parents=1)

TestUtil.register(__name__)


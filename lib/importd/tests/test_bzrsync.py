#!/usr/bin/env python
# Copyright (c) 2005 Canonical Ltd.
# Author: Gustavo Niemeyer <gustavo@niemeyer.net>
#         David Allouche <david@allouche.net>

import logging
import random
import time
import os
import unittest

from bzrlib.branch import Branch as BzrBranch

import transaction
from canonical.launchpad.database import (
    Branch, Revision, RevisionNumber, RevisionParent, RevisionAuthor)

from importd.bzrsync import BzrSync
from importd.tests import TestUtil
from importd.tests.helpers import WebserverHelper, ZopelessUtilitiesHelper


class TestBzrSync(unittest.TestCase):

    AUTHOR = "Revision Author <author@example.com>"
    LOG = "Log message"

    def setUp(self):
        self.webserver_helper = WebserverHelper()
        self.webserver_helper.setUp()
        self.utilities_helper = ZopelessUtilitiesHelper()
        self.utilities_helper.setUp()
        self.setUpBzrBranch()
        self.setUpDBBranch()
        self.setUpAuthor()

    def tearDown(self):
        self.utilities_helper.tearDown()
        self.webserver_helper.tearDown()

    def path(self, name):
        return self.webserver_helper.path(name)

    def url(self, name):
        return self.webserver_helper.get_remote_url(name)

    def setUpBzrBranch(self):
        self.bzr_branch_relpath = "bzr_branch"
        self.bzr_branch_abspath = self.path(self.bzr_branch_relpath)
        self.bzr_branch_url = self.url(self.bzr_branch_relpath)
        os.mkdir(self.bzr_branch_abspath)
        self.bzr_branch = BzrBranch.initialize(self.bzr_branch_abspath)

    def setUpDBBranch(self):
        transaction.begin()
        randomownerid = 1
        self.db_branch = Branch(name="test",
                                url=self.bzr_branch_url,
                                home_page=None,
                                title="Test branch",
                                summary="Branch for testing",
                                product=None,
                                owner=randomownerid)
        transaction.commit()

    def setUpAuthor(self):
        self.db_author = RevisionAuthor.selectOneBy(name=self.AUTHOR)
        if not self.db_author:
            transaction.begin()
            self.db_author = RevisionAuthor(name=self.AUTHOR)
            transaction.commit()

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
        working_tree = self.bzr_branch.working_tree()
        inventory = working_tree.read_working_inventory()
        if not inventory.has_filename("file"):
            working_tree.add("file")
        if message is None:
            message = self.LOG
        if committer is None:
            committer = self.AUTHOR
        working_tree.commit(message, committer=committer)

    def test_empty_branch(self):
        """Importing an empty branch does nothing."""
        counts = self.getCounts()
        BzrSync(transaction, self.db_branch.id).syncHistory()
        self.assertCounts(counts)

    def test_import_revision(self):
        """Importing a revision in history adds one revision and number."""
        self.commitRevision()
        counts = self.getCounts()
        BzrSync(transaction, self.db_branch.id).syncHistory()
        self.assertCounts(counts, new_revisions=1, new_numbers=1)

    def test_import_revision_with_url(self):
        """Importing a revision passing the url parameter works."""
        self.commitRevision()
        counts = self.getCounts()
        bzrsync = BzrSync(transaction, self.db_branch.id, self.bzr_branch_url)
        bzrsync.syncHistory()
        self.assertCounts(counts, new_revisions=1, new_numbers=1)

    def test_new_author(self):
        """Importing a different committer adds it as an author."""
        author = "Another Author <another@example.com>"
        self.commitRevision(committer=author)
        counts = self.getCounts()
        BzrSync(transaction, self.db_branch.id).syncHistory()
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
        BzrSync(transaction, self.db_branch.id).syncHistory()
        self.assertCounts(counts, new_revisions=2, new_numbers=2,
                          new_parents=1)

TestUtil.register(__name__)


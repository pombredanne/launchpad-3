# Copyright 2008, 2009 Canonical Ltd.  All rights reserved.

"""Tests for BranchJobs."""

__metaclass__ = type

import os.path

from unittest import TestLoader

from bzrlib import errors as bzr_errors
from bzrlib.revision import NULL_REVISION
from canonical.testing import DatabaseFunctionalLayer, LaunchpadZopelessLayer
from sqlobject import SQLObjectNotFound
import transaction
from zope.component import getUtility

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.testing import verifyObject
from canonical.launchpad.interfaces.translations import (
    TranslationsBranchImportMode)
from canonical.launchpad.interfaces.translationimportqueue import (
    ITranslationImportQueue, RosettaImportStatus)
from lp.testing import TestCaseWithFactory
from canonical.launchpad.testing.librarianhelpers import (
    get_newest_librarian_file)
from lp.testing.mail_helpers import pop_notifications

from lp.code.interfaces.branchsubscription import (
    BranchSubscriptionNotificationLevel, CodeReviewNotificationLevel)
from lp.code.interfaces.branchjob import (
    IBranchDiffJob, IBranchJob, IRevisionMailJob, IRosettaUploadJob)
from lp.code.interfaces.branchsubscription import (
    BranchSubscriptionDiffSize,)
from lp.code.model.branchjob import (
    BranchDiffJob, BranchJob, BranchJobType, RevisionsAddedJob,
    RevisionMailJob, RosettaUploadJob)
from lp.code.model.branchrevision import BranchRevision
from lp.code.model.revision import RevisionSet


class TestBranchJob(TestCaseWithFactory):
    """Tests for BranchJob."""

    layer = DatabaseFunctionalLayer

    def test_providesInterface(self):
        """Ensure that BranchJob implements IBranchJob."""
        branch = self.factory.makeAnyBranch()
        verifyObject(
            IBranchJob, BranchJob(branch, BranchJobType.STATIC_DIFF, {}))

    def test_destroySelf_destroys_job(self):
        """Ensure that BranchJob.destroySelf destroys the Job as well."""
        branch = self.factory.makeAnyBranch()
        branch_job = BranchJob(branch, BranchJobType.STATIC_DIFF, {})
        job_id = branch_job.job.id
        branch_job.destroySelf()
        self.assertRaises(SQLObjectNotFound, BranchJob.get, job_id)


class TestBranchDiffJob(TestCaseWithFactory):
    """Tests for BranchDiffJob."""

    layer = LaunchpadZopelessLayer

    def test_providesInterface(self):
        """Ensure that BranchDiffJob implements IBranchDiffJob."""
        verifyObject(
            IBranchDiffJob, BranchDiffJob.create(1, '0', '1'))

    def test_run_revision_ids(self):
        """Ensure that run calculates revision ids."""
        self.useBzrBranches()
        branch, tree = self.create_branch_and_tree()
        tree.commit('First commit', rev_id='rev1')
        job = BranchDiffJob.create(branch, '0', '1')
        static_diff = job.run()
        self.assertEqual('null:', static_diff.from_revision_id)
        self.assertEqual('rev1', static_diff.to_revision_id)

    def test_run_diff_content(self):
        """Ensure that run generates expected diff."""
        self.useBzrBranches()
        branch, tree = self.create_branch_and_tree()
        open('file', 'wb').write('foo\n')
        tree.add('file')
        tree.commit('First commit')
        open('file', 'wb').write('bar\n')
        tree.commit('Next commit')
        job = BranchDiffJob.create(branch, '1', '2')
        static_diff = job.run()
        transaction.commit()
        content_lines = static_diff.diff.text.splitlines()
        self.assertEqual(
            content_lines[3:], ['@@ -1,1 +1,1 @@', '-foo', '+bar', ''],
            content_lines[3:])
        self.assertEqual(7, len(content_lines))

    def test_run_is_idempotent(self):
        """Ensure running an equivalent job emits the same diff."""
        self.useBzrBranches()
        branch, tree = self.create_branch_and_tree()
        tree.commit('First commit')
        job1 = BranchDiffJob.create(branch, '0', '1')
        static_diff1 = job1.run()
        job2 = BranchDiffJob.create(branch, '0', '1')
        static_diff2 = job2.run()
        self.assertTrue(static_diff1 is static_diff2)

    def create_rev1_diff(self):
        """Create a StaticDiff for use by test methods.

        This diff contains an add of a file called hello.txt, with contents
        "Hello World\n".
        """
        self.useBzrBranches()
        branch, tree = self.create_branch_and_tree()
        first_revision = 'rev-1'
        tree_transport = tree.bzrdir.root_transport
        tree_transport.put_bytes("hello.txt", "Hello World\n")
        tree.add('hello.txt')
        tree.commit('rev1', timestamp=1e9, timezone=0)
        job = BranchDiffJob.create(branch, '0', '1')
        diff = job.run()
        transaction.commit()
        return diff

    def test_diff_contents(self):
        """Ensure the diff contents match expectations."""
        diff = self.create_rev1_diff()
        expected = (
            "=== added file 'hello.txt'" '\n'
            "--- hello.txt" '\t' "1970-01-01 00:00:00 +0000" '\n'
            "+++ hello.txt" '\t' "2001-09-09 01:46:40 +0000" '\n'
            "@@ -0,0 +1,1 @@" '\n'
            "+Hello World" '\n'
            '\n')
        self.assertEqual(diff.diff.text, expected)

    def test_diff_is_bytes(self):
        """Diffs should be bytestrings.

        Diffs have no single encoding, because they may encompass files in
        multiple encodings.  Therefore, we consider them binary, to avoid
        lossy decoding.
        """
        diff = self.create_rev1_diff()
        self.assertIsInstance(diff.diff.text, str)


class TestRevisionMailJob(TestCaseWithFactory):
    """Tests for BranchDiffJob."""

    layer = LaunchpadZopelessLayer

    def test_providesInterface(self):
        """Ensure that BranchDiffJob implements IBranchDiffJob."""
        branch = self.factory.makeAnyBranch()
        job = RevisionMailJob.create(
            branch, 0, 'from@example.com', 'hello', False, 'subject')
        verifyObject(IRevisionMailJob, job)

    def test_run_sends_mail(self):
        """Ensure RevisionMailJob.run sends mail with correct values."""
        branch = self.factory.makeAnyBranch()
        branch.subscribe(branch.registrant,
            BranchSubscriptionNotificationLevel.FULL,
            BranchSubscriptionDiffSize.WHOLEDIFF,
            CodeReviewNotificationLevel.FULL)
        job = RevisionMailJob.create(
            branch, 0, 'from@example.com', 'hello', False, 'subject')
        job.run()
        (mail,) = pop_notifications()
        self.assertEqual('0', mail['X-Launchpad-Branch-Revision-Number'])
        self.assertEqual('from@example.com', mail['from'])
        self.assertEqual('subject', mail['subject'])
        self.assertEqual(
            'hello\n'
            '\n--\n'
            '%(identity)s\n'
            '%(url)s\n'
            '\nYou are subscribed to branch %(identity)s.\n'
            'To unsubscribe from this branch go to'
            ' %(url)s/+edit-subscription.\n' % {
                'url': canonical_url(branch),
                'identity': branch.bzr_identity
                },
            mail.get_payload(decode=True))

    def test_revno_string(self):
        """Ensure that revnos can be strings."""
        branch = self.factory.makeAnyBranch()
        job = RevisionMailJob.create(
            branch, 'removed', 'from@example.com', 'hello', False, 'subject')
        self.assertEqual('removed', job.revno)

    def test_revno_long(self):
        "Ensure that the revno is a long, not an int."
        branch = self.factory.makeAnyBranch()
        job = RevisionMailJob.create(
            branch, 1, 'from@example.com', 'hello', False, 'subject')
        self.assertIsInstance(job.revno, long)

    def test_perform_diff_performs_diff(self):
        """Ensure that a diff is generated when perform_diff is True."""
        self.useBzrBranches()
        branch, tree = self.create_branch_and_tree()
        tree.bzrdir.root_transport.put_bytes('foo', 'bar\n')
        tree.add('foo')
        tree.commit('First commit')
        job = RevisionMailJob.create(
            branch, 1, 'from@example.com', 'hello', True, 'subject')
        mailer = job.getMailer()
        self.assertIn('+bar\n', mailer.diff)

    def test_perform_diff_ignored_for_revno_0(self):
        """For the null revision, no diff is generated."""
        self.useBzrBranches()
        branch, tree = self.create_branch_and_tree()
        job = RevisionMailJob.create(
            branch, 0, 'from@example.com', 'hello', True, 'subject')
        self.assertIs(None, job.from_revision_spec)
        self.assertIs(None, job.to_revision_spec)
        mailer = job.getMailer()
        self.assertIs(None, mailer.diff)

    def test_iterReady_ignores_BranchDiffJobs(self):
        """Only BranchDiffJobs should not be listed."""
        branch = self.factory.makeAnyBranch()
        BranchDiffJob.create(branch, 0, 1)
        self.assertEqual([], list(RevisionMailJob.iterReady()))

    def test_iterReady_includes_ready_jobs(self):
        """Ready jobs should be listed."""
        branch = self.factory.makeAnyBranch()
        job = RevisionMailJob.create(
            branch, 0, 'from@example.org', 'body', False, 'subject')
        job.job.sync()
        job.context.sync()
        self.assertEqual([job], list(RevisionMailJob.iterReady()))

    def test_iterReady_excludes_unready_jobs(self):
        """Unready jobs should not be listed."""
        branch = self.factory.makeAnyBranch()
        job = RevisionMailJob.create(
            branch, 0, 'from@example.org', 'body', False, 'subject')
        job.job.start()
        job.job.complete()
        self.assertEqual([], list(RevisionMailJob.iterReady()))


class TestRevisionsAddedJob(TestCaseWithFactory):
    """Tests for RevisionsAddedJob."""

    layer = LaunchpadZopelessLayer

    def test_create(self):
        """RevisionsAddedJob.create uses the correct values."""
        branch = self.factory.makeBranch()
        job = RevisionsAddedJob.create(branch, 'rev1', 'rev2', '')
        self.assertEqual('rev1', job.last_scanned_id)
        self.assertEqual('rev2', job.last_revision_id)
        self.assertEqual(branch, job.branch)
        self.assertEqual(
            BranchJobType.REVISIONS_ADDED_MAIL, job.context.job_type)

    def test_iterReady(self):
        """IterReady iterates through ready jobs."""
        branch = self.factory.makeBranch()
        job = RevisionsAddedJob.create(branch, 'rev1', 'rev2', '')
        self.assertEqual([job], list(RevisionsAddedJob.iterReady()))

    def updateDBRevisions(self, branch, bzr_branch, revision_ids=None):
        """Update the database for the revisions.

        :param branch: The database branch associated with the revisions.
        :param bzr_branch: The Bazaar branch associated with the revisions.
        :param revision_ids: The ids of the revisions to update.  If not
            supplied, the branch revision history is used.
        """
        if revision_ids is None:
            revision_ids = bzr_branch.revision_history()
        for bzr_revision in bzr_branch.repository.get_revisions(revision_ids):
            existing = branch.getBranchRevision(
                revision_id=bzr_revision.revision_id)
            if existing is None:
                revision = RevisionSet().newFromBazaarRevision(bzr_revision)
            else:
                revision = RevisionSet().getByRevisionId(
                    bzr_revision.revision_id)
            try:
                revno = bzr_branch.revision_id_to_revno(revision.revision_id)
            except bzr_errors.NoSuchRevision:
                revno = None
            if existing is not None:
                BranchRevision.delete(existing.id)
            branch.createBranchRevision(revno, revision)

    def create3CommitsBranch(self):
        """Create a branch with three commits."""
        branch, tree = self.create_branch_and_tree()
        tree.lock_write()
        try:
            tree.commit('rev1', rev_id='rev1')
            tree.commit('rev2', rev_id='rev2')
            tree.commit('rev3', rev_id='rev3')
            transaction.commit()
            self.layer.switchDbUser('branchscanner')
            self.updateDBRevisions(
                branch, tree.branch, ['rev1', 'rev2', 'rev3'])
        finally:
            tree.unlock()
        return branch, tree

    def test_iterAddedMainline(self):
        """iterAddedMainline iterates through mainline revisions."""
        self.useBzrBranches()
        branch, tree = self.create3CommitsBranch()
        job = RevisionsAddedJob.create(branch, 'rev1', 'rev2', '')
        job.bzr_branch.lock_read()
        self.addCleanup(job.bzr_branch.unlock)
        [(revision, revno)] = list(job.iterAddedMainline())
        self.assertEqual(2, revno)

    def test_iterAddedNonMainline(self):
        """iterAddedMainline drops non-mainline revisions."""
        self.useBzrBranches()
        branch, tree = self.create3CommitsBranch()
        tree.pull(tree.branch, overwrite=True, stop_revision='rev2')
        tree.add_parent_tree_id('rev3')
        tree.commit('rev3a', rev_id='rev3a')
        self.updateDBRevisions(branch, tree.branch, ['rev3', 'rev3a'])
        job = RevisionsAddedJob.create(branch, 'rev1', 'rev3', '')
        job.bzr_branch.lock_read()
        self.addCleanup(job.bzr_branch.unlock)
        out = [x.revision_id for x, y in job.iterAddedMainline()]
        self.assertEqual(['rev2'], out)

    def test_iterAddedMainline_order(self):
        """iterAddedMainline iterates in commit order."""
        self.useBzrBranches()
        branch, tree = self.create3CommitsBranch()
        job = RevisionsAddedJob.create(branch, 'rev1', 'rev3', '')
        job.bzr_branch.lock_read()
        self.addCleanup(job.bzr_branch.unlock)
        # Since we've gone from rev1 to rev3, we've added rev2 and rev3.
        [(rev2, revno2), (rev3, revno3)] = list(job.iterAddedMainline())
        self.assertEqual('rev2', rev2.revision_id)
        self.assertEqual(2, revno2)
        self.assertEqual('rev3', rev3.revision_id)
        self.assertEqual(3, revno3)

    def makeBranchWithCommit(self):
        """Create a branch with a commit."""
        jrandom = self.factory.makePerson(name='jrandom')
        product = self.factory.makeProduct(name='foo')
        branch = self.factory.makeProductBranch(
            name='bar', product=product, owner=jrandom)
        branch.subscribe(branch.registrant,
            BranchSubscriptionNotificationLevel.FULL,
            BranchSubscriptionDiffSize.WHOLEDIFF,
            CodeReviewNotificationLevel.FULL)
        branch, tree = self.create_branch_and_tree(db_branch=branch)
        tree.branch.nick = 'nicholas'
        tree.lock_write()
        self.addCleanup(tree.unlock)
        tree.commit(
            'rev1', rev_id='rev1', timestamp=1000, timezone=0,
            committer='J. Random Hacker <jrandom@example.org>')
        return branch, tree

    def test_getRevisionMessage(self):
        """getRevisionMessage provides a correctly-formatted message."""
        self.useBzrBranches()
        branch, tree = self.makeBranchWithCommit()
        job = RevisionsAddedJob.create(branch, 'rev1', 'rev1', '')
        message = job.getRevisionMessage('rev1', 1)
        self.assertEqual(
        '------------------------------------------------------------\n'
        'revno: 1\n'
        'committer: J. Random Hacker <jrandom@example.org>\n'
        'branch nick: nicholas\n'
        'timestamp: Thu 1970-01-01 00:16:40 +0000\n'
        'message:\n'
        '  rev1\n', message)

    def test_email_format(self):
        """Contents of the email are as expected."""
        self.useBzrBranches()
        db_branch, tree = self.create_branch_and_tree()
        first_revision = 'rev-1'
        tree.bzrdir.root_transport.put_bytes('hello.txt', 'Hello World\n')
        tree.add('hello.txt')
        tree.commit(
            rev_id=first_revision, message="Log message",
            committer="Joe Bloggs <joe@example.com>", timestamp=1000000000.0,
            timezone=0)
        tree.bzrdir.root_transport.put_bytes(
            'hello.txt', 'Hello World\n\nFoo Bar\n')
        second_revision = 'rev-2'
        tree.commit(
            rev_id=second_revision, message="Extended contents",
            committer="Joe Bloggs <joe@example.com>", timestamp=1000100000.0,
            timezone=0)
        transaction.commit()
        self.layer.switchDbUser('branchscanner')
        self.updateDBRevisions(db_branch, tree.branch)
        expected = (
            u"-"*60 + '\n'
            "revno: 1" '\n'
            "committer: Joe Bloggs <joe@example.com>" '\n'
            "branch nick: %s" '\n'
            "timestamp: Sun 2001-09-09 01:46:40 +0000" '\n'
            "message:" '\n'
            "  Log message" '\n'
            "added:" '\n'
            "  hello.txt" '\n' % tree.branch.nick)
        job = RevisionsAddedJob.create(db_branch, '', '', '')
        self.assertEqual(
            job.getRevisionMessage(first_revision, 1), expected)

        expected_diff = (
            "=== modified file 'hello.txt'" '\n'
            "--- hello.txt" '\t' "2001-09-09 01:46:40 +0000" '\n'
            "+++ hello.txt" '\t' "2001-09-10 05:33:20 +0000" '\n'
            "@@ -1,1 +1,3 @@" '\n'
            " Hello World" '\n'
            "+" '\n'
            "+Foo Bar" '\n'
            '\n')
        expected_message = (
            u"-"*60 + '\n'
            "revno: 2" '\n'
            "committer: Joe Bloggs <joe@example.com>" '\n'
            "branch nick: %s" '\n'
            "timestamp: Mon 2001-09-10 05:33:20 +0000" '\n'
            "message:" '\n'
            "  Extended contents" '\n'
            "modified:" '\n'
            "  hello.txt" '\n' % tree.branch.nick)
        tree.branch.lock_read()
        tree.branch.unlock()
        message = job.getRevisionMessage(second_revision, 2)
        self.assertEqual(message, expected_message)

    def test_message_encoding(self):
        """Test handling of non-ASCII commit messages."""
        self.useBzrBranches()
        db_branch, tree = self.create_branch_and_tree()
        rev_id = 'rev-1'
        tree.commit(
            rev_id=rev_id, message=u"Non ASCII: \xe9",
            committer=u"Non ASCII: \xed", timestamp=1000000000.0, timezone=0)
        transaction.commit()
        self.layer.switchDbUser('branchscanner')
        self.updateDBRevisions(db_branch, tree.branch)
        job = RevisionsAddedJob.create(db_branch, '', '', '')
        message = job.getRevisionMessage(rev_id, 1)
        # The revision message must be a unicode object.
        expected = (
            u'-' * 60 + '\n'
            u"revno: 1" '\n'
            u"committer: Non ASCII: \xed" '\n'
            u"branch nick: %s" '\n'
            u"timestamp: Sun 2001-09-09 01:46:40 +0000" '\n'
            u"message:" '\n'
            u"  Non ASCII: \xe9" '\n' % tree.branch.nick)
        self.assertEqual(message, expected)

    def test_getMailerForRevision(self):
        """The mailer for the revision is as expected."""
        self.useBzrBranches()
        branch, tree = self.makeBranchWithCommit()
        revision = tree.branch.repository.get_revision('rev1')
        job = RevisionsAddedJob.create(branch, 'rev1', 'rev1', '')
        mailer = job.getMailerForRevision(revision, 1, True)
        subject = mailer.generateEmail(
            branch.registrant.preferredemail.email, branch.registrant).subject
        self.assertEqual(
            '[Branch ~jrandom/foo/bar] Rev 1: rev1', subject)

    def test_only_nodiff_subscribers_means_no_diff_generated(self):
        """No diff is generated when no subscribers need it."""
        self.layer.switchDbUser('launchpad')
        self.useBzrBranches()
        branch, tree = self.create_branch_and_tree()
        subscriptions = branch.getSubscriptionsByLevel(
            [BranchSubscriptionNotificationLevel.FULL])
        for s in subscriptions:
            s.max_diff_lines = BranchSubscriptionDiffSize.NODIFF
        job = RevisionsAddedJob.create(branch, '', '', '')
        self.assertFalse(job.generateDiffs())


class TestRosettaUploadJob(TestCaseWithFactory):
    """Tests for RosettaUploadJob."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.series = None

    def _makeBranchWithTreeAndFile(self, file_name, file_content = None):
        return self._makeBranchWithTreeAndFiles(((file_name, file_content),))

    def _makeBranchWithTreeAndFiles(self, files):
        """Create a branch with a tree that contains the given files.

        :param files: A list of pairs of file names and file content. file
            content is a byte string and may be None or missing completely,
            in which case an arbitrary unique string is used.
        :returns: The revision of the first commit.
        """
        self.useBzrBranches()
        self.branch, self.tree = self.create_branch_and_tree()
        return self._commitFilesToTree(files, 'First commit')

    def _commitFilesToTree(self, files, commit_message=None):
        """Add files to the tree.

        :param files: A list of pairs of file names and file content. file
            content is a byte string and may be None or missing completely,
            in which case an arbitrary unique string is used.
        :returns: The revision of this commit.
        """
        seen_dirs = set()
        for file_pair in files:
            file_name = file_pair[0]
            dname, fname = os.path.split(file_name)
            if dname != '' and dname not in seen_dirs:
                self.tree.bzrdir.root_transport.mkdir(dname)
                self.tree.add(dname)
                seen_dirs.add(dname)
            try:
                file_content = file_pair[1]
                if file_content is None:
                    raise IndexError # Same as if missing.
            except IndexError:
                file_content = self.factory.getUniqueString()
            self.tree.bzrdir.root_transport.put_bytes(file_name, file_content)
            self.tree.add(file_name)
        if commit_message is None:
            commit_message = self.factory.getUniqueString('commit')
        revision_id = self.tree.commit(commit_message)
        self.branch.last_scanned_id = revision_id
        self.branch.last_mirrored_id = revision_id
        return revision_id

    def _makeProductSeries(self, mode):
        if self.series is None:
            self.series = self.factory.makeProductSeries()
            self.series.branch = self.branch
            self.series.translations_autoimport_mode = mode

    def _runJobWithFile(self, import_mode, file_name, file_content = None):
        return self._runJobWithFiles(
            import_mode, ((file_name, file_content),))

    def _runJobWithFiles(self, import_mode, files,
                         do_upload_translations=False):
        self._makeBranchWithTreeAndFiles(files)
        return self._runJob(import_mode, NULL_REVISION,
                            do_upload_translations)

    def _runJob(self, import_mode, revision_id,
                do_upload_translations=False):
        self._makeProductSeries(import_mode)
        job = RosettaUploadJob.create(self.branch, revision_id,
                                      do_upload_translations)
        if job is not None:
            job.run()
        queue = getUtility(ITranslationImportQueue)
        # Using getAllEntries also asserts that the right product series
        # was used in the upload.
        return list(queue.getAllEntries(target=self.series))

    def test_providesInterface(self):
        # RosettaUploadJob implements IRosettaUploadJob.
        self.branch = self.factory.makeAnyBranch()
        self._makeProductSeries(
            TranslationsBranchImportMode.IMPORT_TEMPLATES)
        job = RosettaUploadJob.create(self.branch, NULL_REVISION)
        verifyObject(IRosettaUploadJob, job)

    def test_upload_pot(self):
        # A POT can be uploaded to a product series that is
        # configured to do so, other files are not uploaded.
        pot_name = "foo.pot"
        entries = self._runJobWithFiles(
            TranslationsBranchImportMode.IMPORT_TEMPLATES,
            ((pot_name,), ('eo.po',), ('README',))
            )
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(pot_name, entry.path)

    def test_upload_pot_subdir(self):
        # A POT can be uploaded from a subdirectory.
        pot_path = "subdir/foo.pot"
        entries = self._runJobWithFile(
            TranslationsBranchImportMode.IMPORT_TEMPLATES, pot_path)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(pot_path, entry.path)

    def test_upload_xpi_template(self):
        # XPI templates are indentified by a special name. They are imported
        # like POT files.
        pot_name = "en-US.xpi"
        entries = self._runJobWithFiles(
            TranslationsBranchImportMode.IMPORT_TEMPLATES,
            ((pot_name,), ('eo.xpi',), ('README',))
            )
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(pot_name, entry.path)

    def test_upload_empty_pot(self):
        # An empty POT cannot be uploaded, if if the product series is
        # configured for template import.
        entries = self._runJobWithFile(
            TranslationsBranchImportMode.IMPORT_TEMPLATES, 'empty.pot', '')
        self.assertEqual(entries, [])

    def test_upload_pot_uploader(self):
        # The uploader of a POT is the series owner.
        entries = self._runJobWithFile(
            TranslationsBranchImportMode.IMPORT_TEMPLATES, 'foo.pot')
        entry = entries[0]
        self.assertEqual(self.series.owner, entry.importer)

    def test_upload_pot_content(self):
        # The content of the uploaded file is stored in the librarian.
        # The uploader of a POT is the series owner.
        POT_CONTENT = "pot content\n"
        entries = self._runJobWithFile(
            TranslationsBranchImportMode.IMPORT_TEMPLATES,
            'foo.pot', POT_CONTENT)
        # Commit so that the file is stored in the librarian.
        transaction.commit()
        self.assertEqual(POT_CONTENT, get_newest_librarian_file().read())

    def test_upload_changed_files(self):
        # Only changed files are queued for import.
        pot_name = "foo.pot"
        revision_id = self._makeBranchWithTreeAndFiles(
            ((pot_name,), ('eo.po',), ('README',)))
        self._commitFilesToTree(((pot_name,),))
        entries = self._runJob(
            TranslationsBranchImportMode.IMPORT_TEMPLATES, revision_id)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(pot_name, entry.path)

    def test_upload_to_no_import_series(self):
        # Nothing can be uploaded to a product series that is
        # not configured to do so.
        entries = self._runJobWithFiles(
            TranslationsBranchImportMode.NO_IMPORT,
            (('foo.pot',), ('eo.po',), ('README',))
            )
        self.assertEqual([], entries)

    def test_upload_translations(self):
        # A PO file can be uploaded if the series is configured for it.
        po_path = "eo.po"
        entries = self._runJobWithFile(
            TranslationsBranchImportMode.IMPORT_TRANSLATIONS, po_path)
        self.assertEqual(1, len(entries))
        entry = entries[0]
        self.assertEqual(po_path, entry.path)

    def test_upload_template_and_translations(self):
        # The same configuration will upload template and translation files
        # in one go. Other files are still ignored.
        entries = self._runJobWithFiles(
            TranslationsBranchImportMode.IMPORT_TRANSLATIONS,
            (('foo.pot',), ('eo.po',), ('fr.po',), ('README',)))
        self.assertEqual(3, len(entries))

    def test_upload_extra_translations_no_import(self):
        # Even if the series is configured not to upload any files, the
        # job can be told to upload template and translation files.
        entries = self._runJobWithFiles(
            TranslationsBranchImportMode.NO_IMPORT,
            (('foo.pot',), ('eo.po',), ('fr.po',), ('README',)), True)
        self.assertEqual(3, len(entries))

    def test_upload_extra_translations_import_templates(self):
        # Even if the series is configured to only upload template files, the
        # job can be told to upload translation files, too.
        entries = self._runJobWithFiles(
            TranslationsBranchImportMode.IMPORT_TEMPLATES,
            (('foo.pot',), ('eo.po',), ('fr.po',), ('README',)), True)
        self.assertEqual(3, len(entries))

    def test_upload_approved(self):
        # A single new entry should be created approved.
        entries = self._runJobWithFile(
            TranslationsBranchImportMode.IMPORT_TEMPLATES, 'foo.pot')
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(RosettaImportStatus.APPROVED, entry.status)

    def test_upload_simplest_case_approved(self):
        # A single new entry should be created approved and linked to the
        # only POTemplate object in the database, if there is only one such
        # object for this product series.
        self._makeBranchWithTreeAndFile('foo.pot')
        self._makeProductSeries(TranslationsBranchImportMode.IMPORT_TEMPLATES)
        potemplate = self.factory.makePOTemplate(self.series)
        entries = self._runJob(None, NULL_REVISION)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(potemplate, entry.potemplate)
        self.assertEqual(RosettaImportStatus.APPROVED, entry.status)

    def test_upload_multiple_approved(self):
        # A single new entry should be created approved and linked to the
        # only POTemplate object in the database, if there is only one such
        # object for this product series.
        self._makeBranchWithTreeAndFiles(
            [('foo.pot', None),('bar.pot', None)])
        self._makeProductSeries(TranslationsBranchImportMode.IMPORT_TEMPLATES)
        self.factory.makePOTemplate(self.series, path='foo.pot')
        self.factory.makePOTemplate(self.series, path='bar.pot')
        entries = self._runJob(None, NULL_REVISION)
        self.assertEqual(len(entries), 2)
        self.assertEqual(RosettaImportStatus.APPROVED, entries[0].status)
        self.assertEqual(RosettaImportStatus.APPROVED, entries[1].status)

    def test_iterReady_job_type(self):
        # iterReady only returns RosettaUploadJobs.
        self._makeBranchWithTreeAndFiles([])
        self._makeProductSeries(
            TranslationsBranchImportMode.IMPORT_TEMPLATES)
        # Add a job that is not a RosettaUploadJob.
        BranchDiffJob.create(self.branch, 0, 1)
        ready_jobs = list(RosettaUploadJob.iterReady())
        self.assertEqual([], ready_jobs)

    def test_iterReady_not_ready(self):
        # iterReady only returns RosettaUploadJobs in ready state.
        self._makeBranchWithTreeAndFiles([])
        self._makeProductSeries(
            TranslationsBranchImportMode.IMPORT_TEMPLATES)
        # Add a job and complete it -> not in ready state.
        job = RosettaUploadJob.create(self.branch, NULL_REVISION)
        job.job.start()
        job.job.complete()
        ready_jobs = list(RosettaUploadJob.iterReady())
        self.assertEqual([], ready_jobs)

    def test_iterReady_revision_ids_differ(self):
        # iterReady does not return jobs for branches where last_scanned_id
        # and last_mirror_id are different.
        self._makeBranchWithTreeAndFiles([])
        self.branch.last_scanned_id = NULL_REVISION # Was not scanned yet.
        self._makeProductSeries(
            TranslationsBranchImportMode.IMPORT_TEMPLATES)
        # Put the job in ready state.
        job = RosettaUploadJob.create(self.branch, NULL_REVISION)
        job.job.sync()
        job.context.sync()
        ready_jobs = list(RosettaUploadJob.iterReady())
        self.assertEqual([], ready_jobs)

    def test_iterReady(self):
        # iterReady only returns RosettaUploadJob in ready state.
        self._makeBranchWithTreeAndFiles([])
        self._makeProductSeries(
            TranslationsBranchImportMode.IMPORT_TEMPLATES)
        # Put the job in ready state.
        job = RosettaUploadJob.create(self.branch, NULL_REVISION)
        job.job.sync()
        job.context.sync()
        ready_jobs = list(RosettaUploadJob.iterReady())
        self.assertEqual([job], ready_jobs)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

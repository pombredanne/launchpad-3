# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for creating BugBranch items based on Bazaar revisions."""

__metaclass__ = type

import unittest

import transaction
from zope.component import getUtility

from canonical.codehosting.scanner.bzrsync import (
    BzrSync, set_bug_branch_status)
from canonical.codehosting.tests.test_scanner_bzrsync import BzrSyncTestCase
from canonical.config import config
from canonical.launchpad.interfaces import (
    BugBranchStatus, IBugBranchSet, IBugSet, NotFoundError)
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.launchpad.webapp import errorlog
from canonical.testing import LaunchpadZopelessLayer


class OopsLoggingTest(unittest.TestCase):
    """Test that temporarily disables the default OOPS reporting and instead
    keeps any OOPSes in a list on the instance.

    :ivar oopses: A list of oopses, [(info, request, now), ...].
    """

    def setUp(self):
        self.oopses = []
        self._globalErrorUtility = errorlog.globalErrorUtility
        errorlog.globalErrorUtility = self

    def tearDown(self):
        self.flushOopses()
        errorlog.globalErrorUtility = self._globalErrorUtility

    def flushOopses(self):
        del self.oopses[:]

    def raising(self, info, request=None, now=None):
        self.oopses.append((info, request, now))

    @property
    def errors(self):
        """Return a list of strings of errors logged via OOPS."""
        errors = []
        for exc_info, script_request, ignored in self.oopses:
            errors.append(str(exc_info[1]))
        return errors


class RevisionPropertyParsing(BzrSyncTestCase, OopsLoggingTest):
    """Tests for parsing the bugs revision property.

    The bugs revision property holds information about Launchpad bugs which are
    affected by a revision. A given revision may affect multiple bugs in
    different ways. A revision may indicate work has begin on a bug, or that it
    constitutes a fix for a bug.

    The bugs property is formatted as a newline-separated list of entries. Each
    entry is of the form '<bug_id> <status>', where '<bug_id>' is the URL for a
    page that describes the bug, and status is one of 'fixed' or 'inprogress'.

    In general, the parser skips over any lines with errors, generating an OOPS
    error for the bad input.

    Blank lines and extraneous whitespace are ignored. URLs for non-Launchpad
    bugs are ignored. The '<status>' field is case-insensitive.

    If the same bug is mentioned more than once, the final mention is
    considered authoritative.
    """

    def setUp(self):
        BzrSyncTestCase.setUp(self)
        OopsLoggingTest.setUp(self)
        self.bzrsync = self.makeBzrSync()

    def test_single(self):
        # Parsing a single line should give a dict with a single entry,
        # mapping the bug_id to the status.
        bugs = self.bzrsync.extractBugInfo(
            "https://launchpad.net/bugs/9999 fixed")
        self.assertEquals([], self.errors)
        self.assertEquals(bugs, {9999: BugBranchStatus.FIXAVAILABLE})

    def test_multiple(self):
        # Information about more than one bug can be specified. Make sure that
        # all the information is processed.
        bugs = self.bzrsync.extractBugInfo(
            "https://launchpad.net/bugs/9999 fixed\n"
            "https://launchpad.net/bugs/8888 fixed")
        self.assertEquals(bugs, {9999: BugBranchStatus.FIXAVAILABLE,
                                 8888: BugBranchStatus.FIXAVAILABLE})

    def test_empty(self):
        # If the property is empty, then return an empty dict.
        bugs = self.bzrsync.extractBugInfo('')
        self.assertEquals(bugs, {})

    def test_bad_status(self):
        # If the given status is invalid or mispelled, then skip it, generate
        # an OOPS, and continue processing.
        bugs = self.bzrsync.extractBugInfo(
            'https://launchpad.net/bugs/9999 faxed')
        self.assertEquals(bugs, {})
        self.assertEquals(
            self.errors, ['Invalid bug status: %r' % 'faxed'])

    def test_continues_processing_on_error(self):
        # Bugs that are mentioned after a bad line are still processed.
        bugs = self.bzrsync.extractBugInfo(
            'https://launchpad.net/bugs/9999 faxed\n'
            'https://launchpad.net/bugs/8888 fixed')
        self.assertEquals(bugs, {8888: BugBranchStatus.FIXAVAILABLE})
        self.assertEquals(
            self.errors, ['Invalid bug status: %r' % 'faxed'])

    def test_bad_bug(self):
        # If the given bug is not a valid integer, then skip it, generate an
        # OOPS and continue processing.
        bugs = self.bzrsync.extractBugInfo(
            'https://launchpad.net/~jml fixed')
        self.assertEquals(bugs, {})
        self.assertEquals(
            self.errors,
            ['Invalid bug reference: https://launchpad.net/~jml'])

    def test_non_launchpad_bug(self):
        # References to bugs on sites other than launchpad are ignored. No
        # OOPS is generated.
        bugs = self.bzrsync.extractBugInfo(
            'http://bugs.debian.org/1234 fixed')
        self.assertEquals(bugs, {})
        self.assertEquals(self.errors, [])

    def test_bad_line(self):
        # If the line is malformed (doesn't contain enough fields), then skip
        # it, generate an OOPS and continue processing.
        bugs = self.bzrsync.extractBugInfo(
            'https://launchpad.net/bugs/9999')
        self.assertEquals(bugs, {})
        self.assertEquals(
            self.errors,
            ['Invalid line: %r' % 'https://launchpad.net/bugs/9999'])

    def test_blank_lines(self):
        # Blank lines should be silently ignored.
        bugs = self.bzrsync.extractBugInfo(
            'https://launchpad.net/bugs/9999 fixed\n\n\n'
            'https://launchpad.net/bugs/8888 fixed\n\n')
        self.assertEquals(bugs, {9999: BugBranchStatus.FIXAVAILABLE,
                                 8888: BugBranchStatus.FIXAVAILABLE})
        self.assertEquals(self.errors, [])

    def test_duplicated_line(self):
        # If a particular line is duplicated, silently ignore the duplicates.
        bugs = self.bzrsync.extractBugInfo(
            'https://launchpad.net/bugs/9999 fixed\n'
            'https://launchpad.net/bugs/9999 fixed')
        self.assertEquals(bugs, {9999: BugBranchStatus.FIXAVAILABLE})

    def test_strict_url_checking(self):
        # Raise an error for a URL that looks like a Launchpad bug URL but
        # isn't.
        bugs = self.bzrsync.extractBugInfo(
            'https://launchpad.net/people/1234 fixed')
        self.assertEquals(bugs, {})
        self.assertEquals(
            self.errors,
            ['Invalid bug reference: https://launchpad.net/people/1234'])

        self.flushOopses()
        bugs = self.bzrsync.extractBugInfo(
            'https://launchpad.net/bugs/foo/1234 fixed')
        self.assertEquals(bugs, {})
        self.assertEquals(
            self.errors,
            ['Invalid bug reference: https://launchpad.net/bugs/foo/1234'])


class TestMakeBugBranch(unittest.TestCase):
    """Tests for making a BugBranch link.

    set_bug_branch_status(bug, branch, status) ensures that a link is created
    between 'bug' and 'branch' and that the relationship is set to 'status'.

    If no such link exists, it creates one. If such a link exists, it updates
    the status.

    There is an exception: if the status is already set to BESTFIX, then we
    won't update it. We do this as a simple measure to avoid overwriting data
    entered on the website.
    """

    layer = LaunchpadZopelessLayer

    def setUp(self):
        factory = LaunchpadObjectFactory()
        self.branch = factory.makeBranch()
        self.bug = factory.makeBug()
        LaunchpadZopelessLayer.txn.commit()
        LaunchpadZopelessLayer.switchDbUser(config.branchscanner.dbuser)

    def assertStatusEqual(self, bug, branch, status):
        """Assert that the BugBranch for `bug` and `branch` has `status`.

        Raises an assertion error if there's no such bug.
        """
        bug_branch = getUtility(IBugBranchSet).getBugBranch(bug, branch)
        if bug_branch is None:
            self.fail('No BugBranch found for %r, %r' % (bug, branch))
        self.assertEqual(bug_branch.status, status)

    def test_makeNewLink(self):
        """set_bug_branch_status makes a BugBranch link if one doesn't
        exist.
        """
        set_bug_branch_status(
            self.bug, self.branch, BugBranchStatus.FIXAVAILABLE)
        self.assertStatusEqual(
            self.bug, self.branch, BugBranchStatus.FIXAVAILABLE)

    def test_registrantIsBranchOwnerOnNewLink(self):
        """When we make a new link, the registrant is the branch owner.

        All BugBranch links have a registrant. When we are creating a link
        based on data in a Bazaar branch, the most obvious registrant is the
        person who asked Launchpad to scan that branch, i.e. the Branch owner.
        """
        set_bug_branch_status(
            self.bug, self.branch, BugBranchStatus.FIXAVAILABLE)
        bug_branch = getUtility(IBugBranchSet).getBugBranch(
            self.bug, self.branch)
        self.assertEqual(self.branch.owner, bug_branch.registrant)

    def test_updateLinkStatus(self):
        """If a link already exists, it updates the status."""
        # Make the initial link.
        set_bug_branch_status(
            self.bug, self.branch, BugBranchStatus.INPROGRESS)
        # Update the status.
        set_bug_branch_status(
            self.bug, self.branch, BugBranchStatus.FIXAVAILABLE)
        self.assertStatusEqual(
            self.bug, self.branch, BugBranchStatus.FIXAVAILABLE)

    def test_doesntDowngradeBestFix(self):
        """set_bug_branch_status doesn't downgrade BESTFIX.

        A BugBranch can have the status 'BESTFIX'. This is generally set on
        the web ui by someone who has taken the time to review branches. We
        don't want to override this status if it has been set.
        """
        # Make the initial link.
        set_bug_branch_status(
            self.bug, self.branch, BugBranchStatus.BESTFIX)
        # Try to update the status.
        # XXX: JonathanLange 2007-12-06: Should this raise an exception?
        set_bug_branch_status(
            self.bug, self.branch, BugBranchStatus.FIXAVAILABLE)
        self.assertStatusEqual(
            self.bug, self.branch, BugBranchStatus.BESTFIX)


# class TestBugLinking(BzrSyncTestCase, OopsLoggingTest):
#     """Tests for automatic bug branch linking."""

#     def setUp(self):
#         BzrSyncTestCase.setUp(self)
#         OopsLoggingTest.setUp(self)

#     def tearDown(self):
#         OopsLoggingTest.tearDown(self)
#         BzrSyncTestCase.tearDown(self)

#     def getLinkedInfo(self, branch):
#         """Return the bugs, revisions and statuses linked to `branch`.

#         Return a list of (bug id, revno, status) for every BugBranch entry
#         associated with `branch`.
#         """
#         bb_set = getUtility(IBugBranchSet)
#         result = []
#         for bug_branch in bb_set.getBugBranchesForBranches([branch]):
#             if bug_branch.revision is None:
#                 revision_id = None
#             else:
#                 revision_id = bug_branch.revision.revision_id
#             result.append((bug_branch.bug.id, revision_id, bug_branch.status))
#         return result

#     def getLinkedBranches(self, bug):
#         """Return a list of unique names of branches linked to `bug`."""
#         return [branch.unique_name for branch in bug.getBranches()]

#     def getLinkedBugs(self, branch):
#         """Return a list of bug IDs linked to `branch`."""
#         bb_set = getUtility(IBugBranchSet)
#         bugs = []
#         for bug_branch in bb_set.getBugBranchesForBranches([branch]):
#             bugs.append(bug_branch.bug.id)
#         return bugs

#     def test_bug_branch_revision_twice(self):
#         # When a branch is scanned twice, it's associated bugs should not
#         # change.
#         self.commitRevision(
#             rev_id='rev1',
#             revprops={'bugs': 'https://launchpad.net/bugs/1 fixed'})
#         self.syncBranch()
#         self.assertEqual([1], self.getLinkedBugs(self.db_branch))
#         self.syncBranch()
#         self.assertEqual([1], self.getLinkedBugs(self.db_branch))

#     def test_branch_which_has_merged_bugfixing_branch(self):
#         # Say branch A has a revision which fixes a bug and that branch A has
#         # been scanned. If branch B merges in branch A and is then scanned,
#         # then branch A should be linked to the bug and branch B should not
#         # be.
#         bug = getUtility(IBugSet).get(1)
#         self.commitRevision(
#             rev_id='rev1',
#             revprops={'bugs': 'https://launchpad.net/bugs/1 fixed'})
#         self.syncBranch()

#         # Branch from the base revision.
#         new_tree, db_branch = self.makeBranch('bzr_branch_merged')
#         new_tree.pull(self.bzr_branch)

#         new_tree.commit(
#             u'commit two', committer=self.AUTHOR, rev_id='r1.1.1',
#             revprops={}, allow_pointless=True)

#         bzrsync = BzrSync(self.txn, db_branch, db_branch.url)
#         bzrsync.syncBranchAndClose()

#         self.assertEqual(
#             [self.db_branch.unique_name], self.getLinkedBranches(bug))

#     def test_branch_which_has_merged_bugfixing_branch_and_fixed_again(self):
#         # Say branch A has a revision which fixes a bug and that branch A has
#         # been scanned. If branch B merges in branch A, commits a revision
#         # which marks that same bug as fixed and is then scanned, then both A
#         # and B are linked to the bug.
#         bug = getUtility(IBugSet).get(1)
#         self.commitRevision(
#             rev_id='rev1',
#             revprops={'bugs': 'https://launchpad.net/bugs/1 fixed'})
#         self.syncBranch()

#         # Branch from the base revision.
#         new_tree, db_branch = self.makeBranch('bzr_branch_merged')
#         new_tree.pull(self.bzr_branch)

#         new_tree.commit(
#             u'commit two', committer=self.AUTHOR, rev_id='r1.1.1',
#             revprops={'bugs': 'https://launchpad.net/bugs/1 fixed'},
#             allow_pointless=True)

#         bzrsync = BzrSync(self.txn, db_branch, db_branch.url)
#         bzrsync.syncBranchAndClose()

#         self.assertEqual(
#             set([db_branch.unique_name, self.db_branch.unique_name]),
#             set(self.getLinkedBranches(bug)))

#     def test_branch_with_overriding_bugfix_updates_bugbranch(self):
#         # Say branch A has a revision which fixes a bug and that branch A has
#         # been scanned. If branch B merges in branch A, commits a revision
#         # which marks that same bug as fixed and is then scanned, then a new
#         # BugBranch row for the bug should be created, pointing at the new
#         # branch.
#         bug = getUtility(IBugSet).get(1)

#         self.commitRevision(
#             rev_id='rev1',
#             revprops={'bugs': 'https://launchpad.net/bugs/1 fixed'})
#         self.syncBranch()

#         # Branch from the base revision.
#         new_tree, db_branch = self.makeBranch('bzr_branch_merged')
#         new_tree.pull(self.bzr_branch)

#         new_tree.commit(
#             u'commit two', committer=self.AUTHOR, rev_id='r1.1.1',
#             revprops={'bugs': 'https://launchpad.net/bugs/1 fixed'},
#             allow_pointless=True)

#         bzrsync = BzrSync(self.txn, db_branch, db_branch.url)
#         bzrsync.syncBranchAndClose()

#         self.assertEqual(
#             set([db_branch.unique_name, self.db_branch.unique_name]),
#             set(self.getLinkedBranches(bug)))

#     def test_makes_bug_branch(self):
#         # If no BugBranch relation exists for the branch and bug, a scan of
#         # the branch should create one.
#         self.assertEqual([], self.getLinkedBugs(self.db_branch))
#         self.commitRevision(
#             rev_id='rev1',
#             revprops={'bugs': 'https://launchpad.net/bugs/1 fixed'})
#         self.syncBranch()
#         self.assertEqual([(1, 'rev1', BugBranchStatus.FIXAVAILABLE)],
#                          self.getLinkedInfo(self.db_branch))

#     def test_multiple_bugs(self):
#         # If a property refers to multiple bugs, create BugBranch links for
#         # all of them.
#         self.assertEqual([], self.getLinkedBugs(self.db_branch))
#         self.commitRevision(
#             rev_id='rev1',
#             revprops={'bugs': 'https://launchpad.net/bugs/1 fixed\n'
#                       'https://launchpad.net/bugs/2 fixed'})
#         self.syncBranch()
#         self.assertEqual(set([1, 2]), set(self.getLinkedBugs(self.db_branch)))

#     def test_newer_revision_updates_status(self):
#         # If the scanner finds a newer revision that fixes a bug in a branch
#         # that already claims to fix a bug, the bug / branch link should be
#         # updated to point at the newer revision.
#         bug = getUtility(IBugSet).get(1)
#         self.commitRevision(
#             rev_id='rev1',
#             revprops={'bugs': 'https://launchpad.net/bugs/1 inprogress\n'})
#         self.syncBranch()
#         self.assertEqual(
#             [(1, 'rev1', BugBranchStatus.INPROGRESS)],
#             self.getLinkedInfo(self.db_branch))
#         self.commitRevision(
#             rev_id='rev2',
#             revprops={'bugs': 'https://launchpad.net/bugs/1 fixed\n'})
#         self.syncBranch()
#         self.assertEqual(
#             [(1, 'rev2', BugBranchStatus.FIXAVAILABLE)],
#             self.getLinkedInfo(self.db_branch))

#     def test_older_revision_doesnt_update_status(self):
#         # If the scanner finds an older revision that fixes a bug in a branch
#         # that already claims to fix the bug, then the bug / branch link
#         # should remain unchanged.
#         #
#         # We need to test this because the scanner add new revisions in a
#         # non-deterministic order.
#         bug = getUtility(IBugSet).get(1)
#         self.commitRevision(
#             timestamp=10 ** 9,
#             rev_id='rev1',
#             revprops={'bugs': 'https://launchpad.net/bugs/1 inprogress\n'})
#         self.syncBranch()
#         self.assertEqual(
#             [(1, 'rev1', BugBranchStatus.INPROGRESS)],
#             self.getLinkedInfo(self.db_branch))
#         self.commitRevision(
#             timestamp=9 * 10 ** 8,
#             rev_id='rev2',
#             revprops={'bugs': 'https://launchpad.net/bugs/1 fixed\n'})
#         self.syncBranch()
#         self.assertEqual(
#             [(1, 'rev1', BugBranchStatus.INPROGRESS)],
#             self.getLinkedInfo(self.db_branch))

#     def test_status_updated_if_no_revision(self):
#         # If the BugBranch link was created or modified on the website, then
#         # the revision will be NULL. If this is the case, then any new
#         # revision found by the scanner should override the revision and
#         # status set on the website.
#         self.txn.begin()
#         bug = getUtility(IBugSet).get(1)
#         bug.addBranch(self.db_branch, status=BugBranchStatus.INPROGRESS)
#         self.txn.commit()
#         self.assertEqual(
#             [(1, None, BugBranchStatus.INPROGRESS)],
#             self.getLinkedInfo(self.db_branch))
#         self.commitRevision(
#             rev_id='rev1',
#             revprops={'bugs': 'https://launchpad.net/bugs/1 fixed\n'})
#         self.syncBranch()
#         self.assertEqual(
#             [(1, 'rev1', BugBranchStatus.FIXAVAILABLE)],
#             self.getLinkedInfo(self.db_branch))

#     def test_oops_on_non_existent_bug(self):
#         # If the bug referred to in the revision properties doesn't actually
#         # exist, then we should generate some sort of OOPS report.
#         self.assertRaises(NotFoundError, getUtility(IBugSet).get, 99999)
#         self.commitRevision(
#             rev_id='rev1',
#             revprops={'bugs': 'https://launchpad.net/bugs/99999 fixed'})
#         self.syncBranch()
#         self.assertEqual(len(self.oopses), 1)

#     def test_revision_properties_in_non_mainline_revision(self):
#         # We look for bug annotations in ''all'' revisions, not just mainline
#         # ones.

#         # Make the base revision.
#         self.bzr_tree.commit(
#             u'common parent', committer=self.AUTHOR, rev_id='r1',
#             allow_pointless=True)

#         # Branch from the base revision.
#         new_tree = self.make_branch_and_tree('bzr_branch_merged')
#         new_tree.pull(self.bzr_branch)

#         # Commit to both branches
#         self.bzr_tree.commit(
#             u'commit one', committer=self.AUTHOR, rev_id='r2',
#             allow_pointless=True)
#         new_tree.commit(
#             u'commit two', committer=self.AUTHOR, rev_id='r1.1.1',
#             revprops={'bugs': 'https://launchpad.net/bugs/1 fixed'},
#             allow_pointless=True)

#         # Merge and commit.
#         self.bzr_tree.merge_from_branch(new_tree.branch)
#         self.commitRevision(
#             u'merge', committer=self.AUTHOR, rev_id='r3',
#             allow_pointless=True)

#         self.syncBranch()

#         self.assertEqual([], self.oopses)
#         self.assertEqual([1], self.getLinkedBugs(self.db_branch))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

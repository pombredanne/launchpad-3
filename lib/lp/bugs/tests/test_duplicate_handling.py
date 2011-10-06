# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for bug duplicate validation."""

from textwrap import dedent

from zope.security.interfaces import ForbiddenAttribute

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.errors import InvalidDuplicateValue
from lp.testing import (
    StormStatementRecorder,
    TestCaseWithFactory,
    )


class TestDuplicateAttributes(TestCaseWithFactory):
    """Test bug attributes related to duplicate handling."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDuplicateAttributes, self).setUp(user='test@canonical.com')

    def setDuplicateofDirectly(self, bug, duplicateof):
        """Helper method to set duplicateof directly."""
        bug.duplicateof = duplicateof

    def test_duplicateof_readonly(self):
        # Test that no one can set duplicateof directly.
        bug = self.factory.makeBug()
        dupe_bug = self.factory.makeBug()
        self.assertRaises(
            ForbiddenAttribute, self.setDuplicateofDirectly, bug, dupe_bug)


class TestMarkDuplicateValidation(TestCaseWithFactory):
    """Test for validation around marking bug duplicates."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestMarkDuplicateValidation, self).setUp(
            user='test@canonical.com')
        self.bug = self.factory.makeBug()
        self.dupe_bug = self.factory.makeBug()
        self.dupe_bug.markAsDuplicate(self.bug)
        self.possible_dupe = self.factory.makeBug()

    def assertDuplicateError(self, bug, duplicateof, msg):
        try:
            bug.markAsDuplicate(duplicateof)
        except InvalidDuplicateValue, err:
            self.assertEqual(str(err), msg)

    def test_error_on_duplicate_to_duplicate(self):
        # Test that a bug cannot be marked a duplicate of
        # a bug that is already itself a duplicate.
        msg = dedent(u"""
            Bug %s is already a duplicate of bug %s. You
            can only mark a bug report as duplicate of one that
            isn't a duplicate itself.
            """ % (
                self.dupe_bug.id, self.dupe_bug.duplicateof.id))
        self.assertDuplicateError(
            self.possible_dupe, self.dupe_bug, msg)

    def test_error_duplicate_to_itself(self):
        # Test that a bug cannot be marked its own duplicate
        msg = dedent(u"""
            You can't mark a bug as a duplicate of itself.""")
        self.assertDuplicateError(self.bug, self.bug, msg)


class TestMoveDuplicates(TestCaseWithFactory):
    """Test duplicates are moved when master bug is marked a duplicate."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestMoveDuplicates, self).setUp(user='test@canonical.com')

    def test_duplicates_are_moved(self):
        # Confirm that a bug with two duplicates can be marked
        # a duplicate of a new bug and that the duplicates will
        # be re-marked as duplicates of the new bug, too.
        bug = self.factory.makeBug()
        dupe_one = self.factory.makeBug()
        dupe_two = self.factory.makeBug()
        dupe_one.markAsDuplicate(bug)
        dupe_two.markAsDuplicate(bug)
        self.assertEqual(dupe_one.duplicateof, bug)
        self.assertEqual(dupe_two.duplicateof, bug)
        new_bug = self.factory.makeBug()
        bug.markAsDuplicate(new_bug)
        self.assertEqual(bug.duplicateof, new_bug)
        self.assertEqual(dupe_one.duplicateof, new_bug)
        self.assertEqual(dupe_two.duplicateof, new_bug)

    def makeBugForDistributionSourcePackage(self, sourcepackage,
                                            with_random_target):
        bug = self.factory.makeBug(
            distribution=sourcepackage.distribution,
            sourcepackagename=sourcepackage.sourcepackagename)
        if with_random_target:
            bug.addTask(
                self.factory.makePerson(),
                self.factory.makeDistributionSourcePackage())
        return bug

    def moveDuplicates(self, number_of_dupes, with_random_target):
        # Create a bug with the given number of duplicates and
        # then mark the bug as a duplicate of another bug.
        # Return the number of SQL statements executed to
        # update the target's bug heat cache
        # (IBugTarget.recalculateBugHeatCache())
        #
        # We use a distributionsourcepackage as the bug target
        # because we filter the recorded SQL statements by
        # string.startswith(...), and the implementation of
        # DistributionSourcePackage.recalculateBugHeatCache()
        # is the only one that issues a "SELECT MAX(Bug.heat)..."
        # query, making it more reliable to detect in the
        # numerous recorded statements compared with the
        # statements issued by BugTarget.recalculateBugHeatCache().
        dsp = self.factory.makeDistributionSourcePackage()
        master_bug = self.makeBugForDistributionSourcePackage(
            dsp, with_random_target)
        for count in xrange(number_of_dupes):
            dupe = self.makeBugForDistributionSourcePackage(
                dsp, with_random_target)
            dupe.markAsDuplicate(master_bug)
        new_master_bug = self.makeBugForDistributionSourcePackage(
            dsp, with_random_target)
        with StormStatementRecorder() as recorder:
            master_bug.markAsDuplicate(new_master_bug)
        target_heat_cache_statements = [
            statement for statement in recorder.statements
            if statement.startswith(
                "SELECT MAX(Bug.heat), SUM(Bug.heat), COUNT(Bug.id)")]
        return len(target_heat_cache_statements)

    def test_move_duplicates_efficient_target_heat_cache_calculation(self):
        # When bug A is marked as a duplicate of bug B, bug A's
        # duplicates become duplicates of bug B too. This requires
        # to set the heat of the duplicates to 0, and to recalculate
        # the heat cache of each target. Ensure that the heat cache
        # is computed only once per target.
        #
        # The query to retrieve the hottest bug for a target is quite
        # slow (ca 200 msec) and should be executed exactly once per
        # target.
        self.assertEqual(1, self.moveDuplicates(2, with_random_target=False))
        self.assertEqual(1, self.moveDuplicates(4, with_random_target=False))

        # If each bug has two targets, one of them common, the other
        # distinct for each bug, we still get one call for each target.
        # For N duplicates, we have N distinct targets, we have
        # the targets for the old master bug and for the new master bug,
        # and one common target, i.e., N+3 targets for N duplicates.
        self.assertEqual(5, self.moveDuplicates(2, with_random_target=True))
        self.assertEqual(7, self.moveDuplicates(4, with_random_target=True))

# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests that the triggers to maintain the branch table transitively_private
   column work correctly."""

__metaclass__ = type

import unittest

from canonical.database.sqlbase import cursor
from canonical.testing.layers import LaunchpadZopelessLayer


class BranchPrivacyTriggersTestCase(unittest.TestCase):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        LaunchpadZopelessLayer.switchDbUser('testadmin')
        self.branch_ids = dict()

    def createBranches(self):
        # Create branches 1, 2, 3, 4, 5
        # 3 is private
        # 4 stacked on 3 at insert time
        # 2 stacked on 5
        # 6 stacked on 1 at insert time
        cur = cursor()
        for x in range(7):
            is_private = 'True' if x == 3 else 'False'
            if x == 4:
                stacked_on = self.branch_ids[3]
            elif x == 6:
                stacked_on = self.branch_ids[1]
            else:
                stacked_on = 'NULL'
            cur.execute("""
                INSERT INTO Branch (
                    name, private, stacked_on, owner, registrant, branch_type
                    )
                    VALUES ('branch%d', %s, %s, 1, 1, 1)
                    RETURNING id
                """ % (x, is_private, stacked_on))
            branch_id = cur.fetchone()[0]
            self.branch_ids[x] = branch_id
        self.updateStackedOnForBranch(2, 5)

    def check_branch_privacy(self, branch_num, expected_private,
                             expected_transitively_private):
        # Check branch_num has the expected privacy attributes.
        is_private = 'True' if expected_private else 'False'
        is_transitively_private = ('True'
            if expected_transitively_private else 'False')
        cur = cursor()
        cur.execute("""
            SELECT COUNT(*)
            FROM Branch
            WHERE id = %s
                AND private is %s
                AND transitively_private is %s
            """ % (self.branch_ids[branch_num],
                   is_private, is_transitively_private))
        self.failUnlessEqual(cur.fetchone()[0], 1)

    def updateStackedOnForBranch(self, branch_num, stacked_on):
        # Update the stacked_on attribute for a branch.
        cur = cursor()
        if stacked_on:
            stacked_on = self.branch_ids[stacked_on]
        else:
            stacked_on = 'NULL'
        cur.execute("""
            UPDATE Branch
            SET stacked_on = %s
            WHERE id = %s
            """ % (stacked_on, self.branch_ids[branch_num]))

    def updatePrivacyForBranch(self, branch_num, private):
        # Update the private attribute for a branch.
        is_private = 'True' if private else 'False'
        cur = cursor()
        cur.execute("""
            UPDATE Branch
            SET private = %s
            WHERE id = %s
            """ % (is_private, self.branch_ids[branch_num]))

    def testInitialBranches(self):
        # Branch inserts invokes the trigger correctly.
        self.createBranches()
        self.check_branch_privacy(1, False, False)
        self.check_branch_privacy(3, True, True)
        self.check_branch_privacy(4, False, True)
        self.check_branch_privacy(6, False, False)

    def testSetStackedOn(self):
        # Stack 1 on 3 which is private.
        # 1 should be transitively private.
        self.createBranches()
        self.updateStackedOnForBranch(1, 3)
        self.check_branch_privacy(1, False, True)

    def testMultiLevelStackedOn(self):
        # 2 is stacked on 5 already.
        # Make 5 private, stack 1 on 2.
        # 1 and 2 should be transitively private.
        self.createBranches()
        self.updatePrivacyForBranch(5, True)
        self.check_branch_privacy(5, True, True)
        self.check_branch_privacy(2, False, True)
        self.updateStackedOnForBranch(1, 2)
        self.check_branch_privacy(1, False, True)
        self.check_branch_privacy(2, False, True)

    def testMultiLevelMultiStackedOn(self):
        # 2 is stacked on 5 already.
        # Stack 4 on 1.
        # Make 5 private, stack 1 on 2.
        # 1, 2 and 4 should be transitively private.
        self.createBranches()
        self.updateStackedOnForBranch(4, 1)
        self.check_branch_privacy(4, False, False)
        self.updatePrivacyForBranch(5, True)
        self.check_branch_privacy(5, True, True)
        self.check_branch_privacy(2, False, True)
        self.updateStackedOnForBranch(1, 2)
        self.check_branch_privacy(1, False, True)
        self.check_branch_privacy(2, False, True)
        self.check_branch_privacy(4, False, True)

    def testRemoveStackedOn(self):
        # 5 is private, 1 stacked on 5, so 1 is transitively private.
        # Unstack 1.
        # 1 should no longer be be transitively private.
        self.createBranches()
        self.updateStackedOnForBranch(1, 5)
        self.updatePrivacyForBranch(5, True)
        self.check_branch_privacy(1, False, True)
        self.updateStackedOnForBranch(1, None)
        self.check_branch_privacy(1, False, False)

    def testSetPrivateTrue(self):
        # Stack 1 on 5, make 5 private.
        # 1 should be transitively private.
        self.createBranches()
        self.updateStackedOnForBranch(1, 5)
        self.check_branch_privacy(1, False, False)
        self.updatePrivacyForBranch(5, True)
        self.check_branch_privacy(5, True, True)
        self.check_branch_privacy(1, False, True)

    def testMultiLevelSetPrivateTrue(self):
        # 2 is stacked on 5 already.
        # Stack 4 on 1, stack 1 on 2
        # Make 5 private.
        # 1, 2 and 4 should be transitively private.
        self.createBranches()
        self.updateStackedOnForBranch(4, 1)
        self.check_branch_privacy(4, False, False)
        self.updateStackedOnForBranch(1, 2)
        self.check_branch_privacy(2, False, False)
        self.updatePrivacyForBranch(5, True)
        self.check_branch_privacy(5, True, True)
        self.check_branch_privacy(1, False, True)
        self.check_branch_privacy(2, False, True)
        self.check_branch_privacy(4, False, True)

    def testSetPrivateFalse(self):
        # Make 5 private, stack 1 on 5.
        # Make 5 public.
        # 1 should not be transitively private.
        self.createBranches()
        self.updatePrivacyForBranch(5, True)
        self.updateStackedOnForBranch(1, 5)
        self.check_branch_privacy(1, False, True)
        self.updatePrivacyForBranch(5, False)
        self.check_branch_privacy(5, False, False)
        self.check_branch_privacy(1, False, False)

    def testMultlLevelSetPrivateFalse(self):
        # 2 is stacked on 5 already.
        # Make 5 private.
        # Stack 4 on 1, stack 1 on 2
        # Make 5 public.
        # 1, 2 and 4 should not be transitively private.
        self.createBranches()
        self.updatePrivacyForBranch(5, True)
        self.updateStackedOnForBranch(4, 1)
        self.updateStackedOnForBranch(1, 2)
        self.check_branch_privacy(1, False, True)
        self.check_branch_privacy(2, False, True)
        self.check_branch_privacy(4, False, True)
        self.check_branch_privacy(5, True, True)
        self.updatePrivacyForBranch(5, False)
        self.check_branch_privacy(1, False, False)
        self.check_branch_privacy(2, False, False)
        self.check_branch_privacy(4, False, False)
        self.check_branch_privacy(5, False, False)

    def testLoopedStackedOn(self):
        # It's possible, although nonsensical, for branch stackings to form a
        # loop. e.g., branch A is stacked on branch B is stacked on branch A.
        # 2 is stacked on 5 already.
        # Stack 1 on 2, stack 5 on 1, completing a 1->2->5 loop.
        # Stack 3 on 3, the trivial case.
        self.createBranches()
        self.updateStackedOnForBranch(1, 2)
        self.updateStackedOnForBranch(5, 1)
        self.updateStackedOnForBranch(3, 3)
        self.updatePrivacyForBranch(5, True)
        self.updatePrivacyForBranch(3, False)
        self.check_branch_privacy(5, True, True)
        self.check_branch_privacy(1, False, True)
        self.check_branch_privacy(2, False, True)
        self.check_branch_privacy(3, False, False)

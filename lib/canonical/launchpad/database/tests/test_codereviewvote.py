from unittest import TestLoader

from canonical.launchpad.ftests import login
from canonical.launchpad.testing import TestCaseWithFactory

class TestCodeReviewVote(TestCaseWithFactory):

    def test_create_vote(self):
        """CodeReviewVotes can be created"""
        merge_proposal = self.factory.makeBranchMergeProposal()
        reviewer = self.factory.makePerson()
        vote = merge_proposal.createVote(reviewer)
        self.assertEqual(reviewer, vote.reviewer)
        self.assertEqual(merge_proposal, vote.branch_merge_proposal)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

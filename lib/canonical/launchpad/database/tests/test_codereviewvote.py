from unittest import TestLoader

from canonical.launchpad.ftests import login
from canonical.launchpad.testing import TestCaseWithFactory

class TestCodeReviewVote(TestCaseWithFactory):

    def test_create_vote(self):
        """CodeReviewVotes can be created"""
        merge_proposal = self.factory.makeBranchMergeProposal()
        reviewer = self.factory.makePerson()
        registrant = self.factory.makePerson()
        vote = merge_proposal.nominateReviewer(reviewer, registrant)
        self.assertEqual(reviewer, vote.reviewer)
        self.assertEqual(registrant, vote.registrant)
        self.assertEqual(merge_proposal, vote.branch_merge_proposal)
        self.assertEqual([vote], list(merge_proposal.votes))


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

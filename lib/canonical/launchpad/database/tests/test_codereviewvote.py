from unittest import TestLoader

from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import ICodeReviewVote
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing import LaunchpadZopelessLayer

class TestCodeReviewVote(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

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
        self.assertSqlAttributeEqualsDate(
            vote, 'date_created', UTC_NOW)
        assert verifyObject(ICodeReviewVote, vote), ('Implements the'
            ' expected interface.')


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

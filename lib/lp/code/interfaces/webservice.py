# Copyright 2009 Canonical Ltd.  All rights reserved.

"""All the interfaces that are exposed through the webservice."""

from lp.code.interfaces.branch import IBranch
from lp.code.interfaces.branches import IBranches
from lp.code.interfaces.branchmergeproposal import IBranchMergeProposal
from lp.code.interfaces.branchsubscription import IBranchSubscription
from lp.code.interfaces.codereviewcomment import ICodeReviewComment
from lp.code.interfaces.codereviewvote import ICodeReviewVoteReference
from lp.code.interfaces.diff import IDiff, IPreviewDiff, IStaticDiff

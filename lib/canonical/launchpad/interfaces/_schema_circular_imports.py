# Copyright 2008-2009 Canonical Ltd.  All rights reserved.

"""Update the interface schema values due to circular imports.

There are situations where there would normally be circular imports to define
the necessary schema values in some interface fields.  To avoid this the
schema is initially set to `Interface`, but this needs to be updated once the
types are defined.
"""

__metaclass__ = type


__all__ = []


from canonical.launchpad.interfaces.branch import IBranch
from canonical.launchpad.interfaces.branchmergeproposal import (
    IBranchMergeProposal)
from canonical.launchpad.interfaces.branchsubscription import (
    IBranchSubscription)
from canonical.launchpad.interfaces.codereviewcomment import (
    CodeReviewVote, ICodeReviewComment)
from canonical.launchpad.interfaces.diff import IPreviewDiff
from canonical.launchpad.interfaces.product import IProduct


IBranch['product'].schema = IProduct
IBranch['landing_targets'].value_type.schema = IBranchMergeProposal
IBranch['landing_candidates'].value_type.schema = IBranchMergeProposal
IBranch['dependent_branches'].value_type.schema = IBranchMergeProposal
IBranch['subscribe'].queryTaggedValue(
    'lazr.webservice.exported')['return_type'].schema = IBranchSubscription

IBranchMergeProposal['getComment'].queryTaggedValue(
    'lazr.webservice.exported')['return_type'].schema = ICodeReviewComment
IBranchMergeProposal['createComment'].queryTaggedValue(
    'lazr.webservice.exported')['params']['vote'].vocabulary = CodeReviewVote
IBranchMergeProposal['createComment'].queryTaggedValue(
    'lazr.webservice.exported')['params']['parent'].schema = \
        ICodeReviewComment
IBranchMergeProposal['all_comments'].value_type.schema = ICodeReviewComment

IPreviewDiff['branch_merge_proposal'].schema = IBranchMergeProposal


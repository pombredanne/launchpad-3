# Copyright 2008-2009 Canonical Ltd.  All rights reserved.

"""Update the interface schema values due to circular imports.

There are situations where there would normally be circular imports to define
the necessary schema values in some interface fields.  To avoid this the
schema is initially set to `Interface`, but this needs to be updated once the
types are defined.
"""

__metaclass__ = type


__all__ = []


from canonical.launchpad.interfaces.build import (
    BuildStatus, IBuild)
from canonical.launchpad.interfaces.buildrecords import IHasBuildRecords
from canonical.launchpad.interfaces.branch import IBranch
from canonical.launchpad.interfaces.branchmergeproposal import (
    BranchMergeProposalStatus, IBranchMergeProposal)
from canonical.launchpad.interfaces.branchsubscription import (
    BranchSubscriptionNotificationLevel, BranchSubscriptionDiffSize,
    CodeReviewNotificationLevel, IBranchSubscription)
from canonical.launchpad.interfaces.codereviewcomment import (
    CodeReviewVote, ICodeReviewComment)
from canonical.launchpad.interfaces.codereviewvote import (
    ICodeReviewVoteReference)
from canonical.launchpad.interfaces.diff import IPreviewDiff
from canonical.launchpad.interfaces.distroseries import IDistroSeries
from canonical.launchpad.interfaces.person import IPerson, IPersonPublic
from canonical.launchpad.interfaces.hwdb import IHWSubmission
from canonical.launchpad.interfaces.product import IProduct
from canonical.launchpad.interfaces.productseries import IProductSeries
from canonical.launchpad.interfaces.publishing import (
    PackagePublishingPocket)
from canonical.launchpad.interfaces.sourcepackage import ISourcePackage


IBranch['product'].schema = IProduct
IBranch['subscriptions'].value_type.schema = IBranchSubscription
IBranch['landing_targets'].value_type.schema = IBranchMergeProposal
IBranch['landing_candidates'].value_type.schema = IBranchMergeProposal
IBranch['dependent_branches'].value_type.schema = IBranchMergeProposal
IBranch['subscribe'].queryTaggedValue(
    'lazr.webservice.exported')['return_type'].schema = IBranchSubscription
IBranch['subscribe'].queryTaggedValue('lazr.webservice.exported')['params'][
    'notification_level'].vocabulary = BranchSubscriptionNotificationLevel
IBranch['subscribe'].queryTaggedValue('lazr.webservice.exported')['params'][
    'max_diff_lines'].vocabulary = BranchSubscriptionDiffSize
IBranch['subscribe'].queryTaggedValue('lazr.webservice.exported')['params'][
    'code_review_level'].vocabulary = CodeReviewNotificationLevel

IBranchMergeProposal['getComment'].queryTaggedValue(
    'lazr.webservice.exported')['return_type'].schema = ICodeReviewComment
IBranchMergeProposal['createComment'].queryTaggedValue(
    'lazr.webservice.exported')['params']['vote'].vocabulary = CodeReviewVote
IBranchMergeProposal['createComment'].queryTaggedValue(
    'lazr.webservice.exported')['params']['parent'].schema = \
        ICodeReviewComment
IBranchMergeProposal['all_comments'].value_type.schema = ICodeReviewComment
IBranchMergeProposal['votes'].value_type.schema = ICodeReviewVoteReference

IPreviewDiff['branch_merge_proposal'].schema = IBranchMergeProposal

IPersonPublic['getMergeProposals'].queryTaggedValue(
    'lazr.webservice.exported')['return_type'].value_type.schema = \
        IBranchMergeProposal
IPersonPublic['getMergeProposals'].queryTaggedValue(
    'lazr.webservice.exported')['params']['status'].value_type.vocabulary = \
        BranchMergeProposalStatus

IHasBuildRecords['getBuildRecords'].queryTaggedValue(
    'lazr.webservice.exported')[
        'params']['pocket'].vocabulary = PackagePublishingPocket
IHasBuildRecords['getBuildRecords'].queryTaggedValue(
    'lazr.webservice.exported')[
        'params']['build_state'].vocabulary = BuildStatus
IHasBuildRecords['getBuildRecords'].queryTaggedValue(
    'lazr.webservice.exported')[
        'return_type'].value_type.schema = IBuild

ISourcePackage['distroseries'].schema = IDistroSeries
ISourcePackage['productseries'].schema = IProductSeries
ISourcePackage['getBranch'].queryTaggedValue(
    'lazr.webservice.exported')[
        'params']['pocket'].vocabulary = PackagePublishingPocket
ISourcePackage['getBranch'].queryTaggedValue(
    'lazr.webservice.exported')['return_type'].schema = IBranch
ISourcePackage['setBranch'].queryTaggedValue(
    'lazr.webservice.exported')[
        'params']['pocket'].vocabulary = PackagePublishingPocket
ISourcePackage['setBranch'].queryTaggedValue(
    'lazr.webservice.exported')['params']['branch'].schema = IBranch

IPerson['hardware_submissions'].value_type.schema = IHWSubmission

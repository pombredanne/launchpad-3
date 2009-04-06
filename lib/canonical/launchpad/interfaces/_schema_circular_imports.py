# Copyright 2008-2009 Canonical Ltd.  All rights reserved.

"""Update the interface schema values due to circular imports.

There are situations where there would normally be circular imports to define
the necessary schema values in some interface fields.  To avoid this the
schema is initially set to `Interface`, but this needs to be updated once the
types are defined.
"""

__metaclass__ = type


__all__ = []


from lazr.restful.declarations import LAZR_WEBSERVICE_EXPORTED

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
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.person import IPerson, IPersonPublic
from canonical.launchpad.interfaces.hwdb import IHWSubmission
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries
from canonical.launchpad.interfaces.publishing import (
    PackagePublishingPocket)
from lp.registry.interfaces.sourcepackage import ISourcePackage


IBranch['product'].schema = IProduct
IBranch['subscriptions'].value_type.schema = IBranchSubscription
IBranch['landing_targets'].value_type.schema = IBranchMergeProposal
IBranch['landing_candidates'].value_type.schema = IBranchMergeProposal
IBranch['dependent_branches'].value_type.schema = IBranchMergeProposal
IBranch['subscribe'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['return_type'].schema = IBranchSubscription
IBranch['subscribe'].queryTaggedValue(LAZR_WEBSERVICE_EXPORTED)['params'][
    'notification_level'].vocabulary = BranchSubscriptionNotificationLevel
IBranch['subscribe'].queryTaggedValue(LAZR_WEBSERVICE_EXPORTED)['params'][
    'max_diff_lines'].vocabulary = BranchSubscriptionDiffSize
IBranch['subscribe'].queryTaggedValue(LAZR_WEBSERVICE_EXPORTED)['params'][
    'code_review_level'].vocabulary = CodeReviewNotificationLevel

IBranchMergeProposal['getComment'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['return_type'].schema = ICodeReviewComment
IBranchMergeProposal['createComment'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['params']['vote'].vocabulary = CodeReviewVote
IBranchMergeProposal['createComment'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['params']['parent'].schema = \
        ICodeReviewComment
IBranchMergeProposal['all_comments'].value_type.schema = ICodeReviewComment
IBranchMergeProposal['votes'].value_type.schema = ICodeReviewVoteReference

IPreviewDiff['branch_merge_proposal'].schema = IBranchMergeProposal

IPersonPublic['getMergeProposals'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['return_type'].value_type.schema = \
        IBranchMergeProposal
IPersonPublic['getMergeProposals'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['params']['status'].value_type.vocabulary = \
        BranchMergeProposalStatus

IHasBuildRecords['getBuildRecords'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)[
        'params']['pocket'].vocabulary = PackagePublishingPocket
IHasBuildRecords['getBuildRecords'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)[
        'params']['build_state'].vocabulary = BuildStatus
IHasBuildRecords['getBuildRecords'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)[
        'return_type'].value_type.schema = IBuild

ISourcePackage['distroseries'].schema = IDistroSeries
ISourcePackage['productseries'].schema = IProductSeries
ISourcePackage['getBranch'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)[
        'params']['pocket'].vocabulary = PackagePublishingPocket
ISourcePackage['getBranch'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['return_type'].schema = IBranch
ISourcePackage['setBranch'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)[
        'params']['pocket'].vocabulary = PackagePublishingPocket
ISourcePackage['setBranch'].queryTaggedValue(
    LAZR_WEBSERVICE_EXPORTED)['params']['branch'].schema = IBranch

IPerson['hardware_submissions'].value_type.schema = IHWSubmission

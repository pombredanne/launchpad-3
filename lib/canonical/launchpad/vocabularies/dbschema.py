# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""
You probably don't want to import stuff from here. See __init__.py
for details
"""

__metaclass__ = type

__all__ = [
    'vocab_factory',
    'BountyDifficultyVocabulary',
    'BountyStatusVocabulary',
    'BranchLifecycleStatusVocabulary',
    'BranchLifecycleStatusFilterVocabulary',
    'BranchReviewStatusVocabulary',
    'BranchSubscriptionDiffSizeVocabulary',
    'BranchSubscriptionNotificationLevelVocabulary',
    'BugAttachmentTypeVocabulary',
    'BugRefVocabulary',
    'BugBranchStatusVocabulary',
    'BugNominationStatusVocabulary',
    'BugTaskImportanceVocabulary',
    'BugTaskStatusVocabulary',
    'BugTrackerTypeVocabulary',
    'CveStatusVocabulary',
    'DistributionReleaseStatusVocabulary',
    'GPGKeyAlgorithmVocabulary',
    'InfestationStatusVocabulary',
    'MirrorContentVocabulary',
    'MirrorPulseTypeVocabulary',
    'MirrorSpeedVocabulary',
    'MirrorStatusVocabulary',
    'PackagePublishingPocketVocabulary',
    'PackagingTypeVocabulary',
    'PollAlgorithmVocabulary',
    'PollSecrecyVocabulary',
    'QuestionActionVocabulary',
    'QuestionPriorityVocabulary',
    'QuestionSortVocabulary',
    'QuestionStatusVocabulary',
    'RemoteBugTaskImportanceVocabulary',
    'RemoteBugTaskStatusVocabulary',
    'RevisionControlSystemsVocabulary',
    'ShipItFlavourVocabulary',
    'SpecificationDeliveryVocabulary',
    'SpecificationPriorityVocabulary',
    'SpecificationStatusVocabulary',
    'SpecificationGoalStatusVocabulary',
    'SprintSpecificationStatusVocabulary',
    'TeamMembershipRenewalPolicyVocabulary',
    'TeamSubscriptionPolicyVocabulary',
    'TextDirectionVocabulary',
    'TranslationPermissionVocabulary',
    'UpstreamFileTypeVocabulary',
    ]

from canonical.lp import dbschema

from canonical.launchpad.webapp.vocabulary import (
    sortkey_ordered_vocab_factory, vocab_factory)


# DB Schema Vocabularies

BountyDifficultyVocabulary = vocab_factory(dbschema.BountyDifficulty)
BountyStatusVocabulary = vocab_factory(dbschema.BountyStatus)
BranchLifecycleStatusVocabulary = \
    vocab_factory(dbschema.BranchLifecycleStatus)
BranchLifecycleStatusFilterVocabulary = \
    vocab_factory(dbschema.BranchLifecycleStatusFilter)
BranchReviewStatusVocabulary = vocab_factory(dbschema.BranchReviewStatus)
BranchSubscriptionDiffSizeVocabulary = \
    sortkey_ordered_vocab_factory(dbschema.BranchSubscriptionDiffSize)
BranchSubscriptionNotificationLevelVocabulary = \
    vocab_factory(dbschema.BranchSubscriptionNotificationLevel)
BugAttachmentTypeVocabulary = vocab_factory(dbschema.BugAttachmentType)
BugBranchStatusVocabulary = vocab_factory(dbschema.BugBranchStatus)
BugNominationStatusVocabulary = vocab_factory(dbschema.BugNominationStatus)
BugTaskStatusVocabulary = vocab_factory(
    dbschema.BugTaskStatus, noshow=[dbschema.BugTaskStatus.UNKNOWN])
BugTaskImportanceVocabulary = vocab_factory(
    dbschema.BugTaskImportance, noshow=[dbschema.BugTaskImportance.UNKNOWN])
BugRefVocabulary = vocab_factory(dbschema.BugExternalReferenceType)
BugTrackerTypeVocabulary = vocab_factory(dbschema.BugTrackerType,
    noshow=[dbschema.BugTrackerType.DEBBUGS,
            dbschema.BugTrackerType.SOURCEFORGE])
CveStatusVocabulary = vocab_factory(dbschema.CveStatus)
DistributionReleaseStatusVocabulary = vocab_factory(dbschema.DistributionReleaseStatus)
GPGKeyAlgorithmVocabulary = vocab_factory(dbschema.GPGKeyAlgorithm)
InfestationStatusVocabulary = vocab_factory(dbschema.BugInfestationStatus)
MirrorContentVocabulary = vocab_factory(dbschema.MirrorContent)
MirrorPulseTypeVocabulary = vocab_factory(dbschema.MirrorPulseType)
MirrorSpeedVocabulary = vocab_factory(dbschema.MirrorSpeed)
MirrorStatusVocabulary = vocab_factory(dbschema.MirrorStatus)
PackagePublishingPocketVocabulary = vocab_factory(
    dbschema.PackagePublishingPocket)
PackagingTypeVocabulary = vocab_factory(dbschema.PackagingType)
PollAlgorithmVocabulary = vocab_factory(dbschema.PollAlgorithm)
PollSecrecyVocabulary = vocab_factory(dbschema.PollSecrecy)
QuestionActionVocabulary = vocab_factory(dbschema.QuestionAction)
QuestionSortVocabulary =  vocab_factory(dbschema.QuestionSort)
QuestionStatusVocabulary =  vocab_factory(dbschema.QuestionStatus)
QuestionPriorityVocabulary = vocab_factory(dbschema.QuestionPriority)
RemoteBugTaskStatusVocabulary = vocab_factory(dbschema.BugTaskStatus)
RemoteBugTaskImportanceVocabulary = vocab_factory(dbschema.BugTaskImportance)
RevisionControlSystemsVocabulary = vocab_factory(
    dbschema.RevisionControlSystems)
ShipItFlavourVocabulary = vocab_factory(dbschema.ShipItFlavour)
SpecificationDeliveryVocabulary =  vocab_factory(dbschema.SpecificationDelivery)
SpecificationPriorityVocabulary = vocab_factory(dbschema.SpecificationPriority)
SpecificationStatusVocabulary =  vocab_factory(dbschema.SpecificationStatus)
SpecificationGoalStatusVocabulary = vocab_factory(dbschema.SpecificationGoalStatus)
SprintSpecificationStatusVocabulary =  vocab_factory(dbschema.SprintSpecificationStatus)
TeamMembershipRenewalPolicyVocabulary = vocab_factory(
    dbschema.TeamMembershipRenewalPolicy)
TeamSubscriptionPolicyVocabulary = vocab_factory(
    dbschema.TeamSubscriptionPolicy)
TextDirectionVocabulary =  vocab_factory(dbschema.TextDirection)
TranslationPermissionVocabulary = vocab_factory(dbschema.TranslationPermission)
UpstreamFileTypeVocabulary = vocab_factory(dbschema.UpstreamFileType)


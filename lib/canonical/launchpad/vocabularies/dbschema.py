# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

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
    'RemoteBugTaskImportanceVocabulary',
    'RemoteBugTaskStatusVocabulary',
    'RevisionControlSystemsVocabulary',
    'ShipItFlavourVocabulary',
    'SpecificationDeliveryVocabulary',
    'SpecificationPriorityVocabulary',
    'SpecificationStatusVocabulary',
    'SpecificationGoalStatusVocabulary',
    'SprintSpecificationStatusVocabulary',
    'TeamSubscriptionPolicyVocabulary',
    'TicketActionVocabulary',
    'TicketPriorityVocabulary',
    'TicketSortVocabulary',
    'TicketStatusVocabulary',
    'TranslationPermissionVocabulary',
    'UpstreamFileTypeVocabulary',
    ]

from canonical.lp import dbschema
from zope.schema.vocabulary import SimpleVocabulary

# TODO: Make DBSchema classes provide an interface, so we can adapt IDBSchema
# to IVocabulary
def vocab_factory(schema, noshow=[]):
    """Factory for IDBSchema -> IVocabulary adapters.

    This function returns a callable object that creates vocabularies
    from dbschemas.

    The items appear in value order, lowest first.
    """
    def factory(context, schema=schema, noshow=noshow):
        """Adapt IDBSchema to IVocabulary."""
        # XXX kiko: we should use sort's built-in DSU here.
        items = [(item.value, item.title, item)
            for item in schema.items
            if item not in noshow]
        items.sort()
        items = [(title, value) for sortkey, title, value in items]
        return SimpleVocabulary.fromItems(items)
    return factory

# DB Schema Vocabularies

BountyDifficultyVocabulary = vocab_factory(dbschema.BountyDifficulty)
BountyStatusVocabulary = vocab_factory(dbschema.BountyStatus)
BranchLifecycleStatusVocabulary = \
    vocab_factory(dbschema.BranchLifecycleStatus)
BranchLifecycleStatusFilterVocabulary = \
    vocab_factory(dbschema.BranchLifecycleStatusFilter)
BranchReviewStatusVocabulary = vocab_factory(dbschema.BranchReviewStatus)
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
TeamSubscriptionPolicyVocabulary = vocab_factory(
        dbschema.TeamSubscriptionPolicy)
TicketActionVocabulary = vocab_factory(dbschema.TicketAction)
TicketSortVocabulary =  vocab_factory(dbschema.TicketSort)
TicketStatusVocabulary =  vocab_factory(dbschema.TicketStatus)
TicketPriorityVocabulary = vocab_factory(dbschema.TicketPriority)
TranslationPermissionVocabulary = vocab_factory(dbschema.TranslationPermission)
UpstreamFileTypeVocabulary = vocab_factory(dbschema.UpstreamFileType)

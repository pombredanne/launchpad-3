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
    'BranchReviewStatusVocabulary',
    'BugAttachmentTypeVocabulary',
    'BugRefVocabulary',
    'BugTaskPriorityVocabulary',
    'BugTaskSeverityVocabulary',
    'BugTaskStatusVocabulary',
    'BugTrackerTypeVocabulary',
    'CveStatusVocabulary',
    'DistributionReleaseStatusVocabulary',
    'GPGKeyAlgorithmVocabulary',
    'InfestationStatusVocabulary',
    'KarmaActionCategoryVocabulary',
    'PackagingTypeVocabulary',
    'PollAlgorithmVocabulary',
    'PollSecrecyVocabulary',
    'SpecificationStatusVocabulary',
    'SpecificationPriorityVocabulary',
    'SprintSpecificationStatusVocabulary',
    'TeamSubscriptionPolicyVocabulary',
    'TicketPriorityVocabulary',
    'TicketStatusVocabulary',
    'TranslationPermissionVocabulary',
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
BranchReviewStatusVocabulary = vocab_factory(dbschema.BranchReviewStatus)
BugAttachmentTypeVocabulary = vocab_factory(dbschema.BugAttachmentType)
BugTaskStatusVocabulary = vocab_factory(dbschema.BugTaskStatus)
BugTaskPriorityVocabulary = vocab_factory(dbschema.BugTaskPriority)
BugTaskSeverityVocabulary = vocab_factory(dbschema.BugTaskSeverity)
BugRefVocabulary = vocab_factory(dbschema.BugExternalReferenceType)
BugTrackerTypeVocabulary = vocab_factory(dbschema.BugTrackerType,
    noshow=[dbschema.BugTrackerType.DEBBUGS])
CveStatusVocabulary = vocab_factory(dbschema.CveStatus)
DistributionReleaseStatusVocabulary = vocab_factory(dbschema.DistributionReleaseStatus)
GPGKeyAlgorithmVocabulary = vocab_factory(dbschema.GPGKeyAlgorithm)
InfestationStatusVocabulary = vocab_factory(dbschema.BugInfestationStatus)
KarmaActionCategoryVocabulary = vocab_factory(dbschema.KarmaActionCategory)
PackagingTypeVocabulary = vocab_factory(dbschema.PackagingType)
PollAlgorithmVocabulary = vocab_factory(dbschema.PollAlgorithm)
PollSecrecyVocabulary = vocab_factory(dbschema.PollSecrecy)
SpecificationStatusVocabulary =  vocab_factory(dbschema.SpecificationStatus)
SpecificationPriorityVocabulary = vocab_factory(dbschema.SpecificationPriority)
SprintSpecificationStatusVocabulary =  vocab_factory(dbschema.SprintSpecificationStatus)
TeamSubscriptionPolicyVocabulary = vocab_factory(
        dbschema.TeamSubscriptionPolicy)
TicketStatusVocabulary =  vocab_factory(dbschema.TicketStatus)
TicketPriorityVocabulary = vocab_factory(dbschema.TicketPriority)
TranslationPermissionVocabulary = vocab_factory(dbschema.TranslationPermission)


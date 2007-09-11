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
    'BranchReviewStatusVocabulary',
    'BugAttachmentTypeVocabulary',
    'BugRefVocabulary',
    'BugNominationStatusVocabulary',
    'BugTaskImportanceVocabulary',
    'BugTaskStatusVocabulary',
    'BugTrackerTypeVocabulary',
    'CodeImportReviewStatusVocabulary',
    'CveStatusVocabulary',
    'DistroSeriesStatusVocabulary',
    'InfestationStatusVocabulary',
    'PackagePublishingPocketVocabulary',
    'PackagingTypeVocabulary',
    'PollAlgorithmVocabulary',
    'PollSecrecyVocabulary',
    'RemoteBugTaskImportanceVocabulary',
    'RemoteBugTaskStatusVocabulary',
    'RevisionControlSystemsVocabulary',
    'SpecificationImplementationStatusVocabulary',
    'SpecificationPriorityVocabulary',
    'SpecificationDefinitionStatusVocabulary',
    'SpecificationGoalStatusVocabulary',
    'SprintSpecificationStatusVocabulary',
    'TextDirectionVocabulary',
    'TranslationFileFormatVocabulary',
    'TranslationPermissionVocabulary',
    'UpstreamFileTypeVocabulary',
    ]

from canonical.lp import dbschema

from canonical.launchpad.webapp.vocabulary import vocab_factory


# DB Schema Vocabularies

BountyDifficultyVocabulary = vocab_factory(dbschema.BountyDifficulty)
BountyStatusVocabulary = vocab_factory(dbschema.BountyStatus)
BranchReviewStatusVocabulary = vocab_factory(dbschema.BranchReviewStatus)
BugAttachmentTypeVocabulary = vocab_factory(dbschema.BugAttachmentType)
BugNominationStatusVocabulary = vocab_factory(dbschema.BugNominationStatus)
BugTaskStatusVocabulary = vocab_factory(
    dbschema.BugTaskStatus, noshow=[dbschema.BugTaskStatus.UNKNOWN])
BugTaskImportanceVocabulary = vocab_factory(
    dbschema.BugTaskImportance, noshow=[dbschema.BugTaskImportance.UNKNOWN])
BugRefVocabulary = vocab_factory(dbschema.BugExternalReferenceType)
BugTrackerTypeVocabulary = vocab_factory(dbschema.BugTrackerType,
    noshow=[dbschema.BugTrackerType.DEBBUGS,
            dbschema.BugTrackerType.SOURCEFORGE])
CodeImportReviewStatusVocabulary = vocab_factory(
    dbschema.CodeImportReviewStatus)
CveStatusVocabulary = vocab_factory(dbschema.CveStatus)
DistroSeriesStatusVocabulary = vocab_factory(dbschema.DistroSeriesStatus)
InfestationStatusVocabulary = vocab_factory(dbschema.BugInfestationStatus)
PackagePublishingPocketVocabulary = vocab_factory(
    dbschema.PackagePublishingPocket)
PackagingTypeVocabulary = vocab_factory(dbschema.PackagingType)
PollAlgorithmVocabulary = vocab_factory(dbschema.PollAlgorithm)
PollSecrecyVocabulary = vocab_factory(dbschema.PollSecrecy)
RemoteBugTaskStatusVocabulary = vocab_factory(dbschema.BugTaskStatus)
RemoteBugTaskImportanceVocabulary = vocab_factory(dbschema.BugTaskImportance)
RevisionControlSystemsVocabulary = vocab_factory(
    dbschema.RevisionControlSystems)
SpecificationImplementationStatusVocabulary =  vocab_factory(dbschema.SpecificationImplementationStatus)
SpecificationPriorityVocabulary = vocab_factory(dbschema.SpecificationPriority)
SpecificationDefinitionStatusVocabulary =  vocab_factory(dbschema.SpecificationDefinitionStatus)
SpecificationGoalStatusVocabulary = vocab_factory(dbschema.SpecificationGoalStatus)
SprintSpecificationStatusVocabulary =  vocab_factory(dbschema.SprintSpecificationStatus)
TextDirectionVocabulary =  vocab_factory(dbschema.TextDirection)
TranslationFileFormatVocabulary = vocab_factory(dbschema.TranslationFileFormat)
TranslationPermissionVocabulary = vocab_factory(dbschema.TranslationPermission)
UpstreamFileTypeVocabulary = vocab_factory(dbschema.UpstreamFileType)

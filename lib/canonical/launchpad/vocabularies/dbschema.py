# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""
You probably don't want to import stuff from here. See __init__.py
for details
"""

__metaclass__ = type

__all__ = [
    'vocab_factory',
    'BranchReviewStatusVocabulary',
    'BugAttachmentTypeVocabulary',
    'BugRefVocabulary',
    'BugNominationStatusVocabulary',
    'BugTaskImportanceVocabulary',
    'BugTrackerTypeVocabulary',
    'CodeImportReviewStatusVocabulary',
    'CveStatusVocabulary',
    'DistroSeriesStatusVocabulary',
    'InfestationStatusVocabulary',
    'PackagePublishingPocketVocabulary',
    'RemoteBugTaskImportanceVocabulary',
    'SpecificationImplementationStatusVocabulary',
    'SpecificationPriorityVocabulary',
    'SpecificationDefinitionStatusVocabulary',
    'SpecificationGoalStatusVocabulary',
    'SprintSpecificationStatusVocabulary',
    'TranslationFileFormatVocabulary',
    'TranslationPermissionVocabulary',
    ]

from canonical.lp import dbschema

from canonical.launchpad.webapp.vocabulary import vocab_factory
from canonical.launchpad.interfaces import (
    TranslationFileFormat, TranslationPermission)


# DB Schema Vocabularies

BranchReviewStatusVocabulary = vocab_factory(dbschema.BranchReviewStatus)
BugAttachmentTypeVocabulary = vocab_factory(dbschema.BugAttachmentType)
BugNominationStatusVocabulary = vocab_factory(dbschema.BugNominationStatus)
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
RemoteBugTaskImportanceVocabulary = vocab_factory(dbschema.BugTaskImportance)
SpecificationImplementationStatusVocabulary =  vocab_factory(dbschema.SpecificationImplementationStatus)
SpecificationPriorityVocabulary = vocab_factory(dbschema.SpecificationPriority)
SpecificationDefinitionStatusVocabulary =  vocab_factory(dbschema.SpecificationDefinitionStatus)
SpecificationGoalStatusVocabulary = vocab_factory(dbschema.SpecificationGoalStatus)
SprintSpecificationStatusVocabulary =  vocab_factory(dbschema.SprintSpecificationStatus)
TranslationFileFormatVocabulary = vocab_factory(TranslationFileFormat)
TranslationPermissionVocabulary = vocab_factory(TranslationPermission)

from canonical.lp import dbschema

# DB Schema Vocabularies
SubscriptionVocabulary = dbschema.vocabulary(dbschema.BugSubscription)
BugStatusVocabulary = dbschema.vocabulary(dbschema.BugAssignmentStatus)
BugPriorityVocabulary = dbschema.vocabulary(dbschema.BugPriority)
BugSeverityVocabulary = dbschema.vocabulary(dbschema.BugSeverity)
BugRefVocabulary = dbschema.vocabulary(dbschema.BugExternalReferenceType)
InfestationStatusVocabulary = dbschema.vocabulary(dbschema.BugInfestationStatus)
#RemoteBugStatusVocabulary = dbschema.vocabulary(dbschema.RemoteBugStatus)


from zope.schema.vocabulary import SimpleVocabulary
from canonical.lp import dbschema
from zope.schema.interfaces import IVocabulary

SubscriptionVocabulary = dbschema.vocabulary(dbschema.BugSubscription)
#SubscriptionVocabulary = SimpleVocabulary.fromItems([(0, u'watch'),
#                                                     (1, u'cc'),
#                                                     (2, u'ignore')])

InfestationVocabulary = dbschema.vocabulary(dbschema.BugInfestationStatus)
                                                    
BugStatusVocabulary = dbschema.vocabulary(dbschema.BugAssignmentStatus)

BugPriorityVocabulary = dbschema.vocabulary(dbschema.BugPriority)

BugSeverityVocabulary = dbschema.vocabulary(dbschema.BugSeverity)

BugRefVocabulary = dbschema.vocabulary(dbschema.BugExternalReferenceType)


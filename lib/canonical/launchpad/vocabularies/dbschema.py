'''
You probably don't want to import stuff from here. See __init__.py
for details
'''
from canonical.lp import dbschema
from zope.schema.vocabulary import SimpleVocabulary

# TODO: Make DBSchema classes provide an interface, so we can adapt IDBSchema
# to IVocabulary
def vocab_factory(schema):
    '''Adapt IDBSchema to IVocabulary'''
    def factory(context, schema=schema):
        return SimpleVocabulary.fromItems([
            (i.title, int(i)) for i in [getattr(schema, a) for a in dir(schema)]
            if isinstance(i, dbschema.Item)
            ])
    return factory

# DB Schema Vocabularies
SubscriptionVocabulary = vocab_factory(dbschema.BugSubscription)
BugStatusVocabulary = vocab_factory(dbschema.BugTaskStatus)
BugPriorityVocabulary = vocab_factory(dbschema.BugPriority)
BugSeverityVocabulary = vocab_factory(dbschema.BugSeverity)
BugRefVocabulary = vocab_factory(dbschema.BugExternalReferenceType)
InfestationStatusVocabulary = vocab_factory(dbschema.BugInfestationStatus)
#RemoteBugStatusVocabulary = vocab_factory(dbschema.RemoteBugStatus)


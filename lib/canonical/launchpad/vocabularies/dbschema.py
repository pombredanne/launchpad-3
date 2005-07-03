"""
You probably don't want to import stuff from here. See __init__.py
for details
"""
from canonical.lp import dbschema
from zope.schema.vocabulary import SimpleVocabulary

# TODO: Make DBSchema classes provide an interface, so we can adapt IDBSchema
# to IVocabulary
def vocab_factory(schema):
    """Factory for IDBSchema -> IVocabulary adapters.

    This function returns a callable object that creates vocabularies
    from dbschemas.

    The items appear in value order, lowest first.
    """
    def factory(context, schema=schema):
        """Adapt IDBSchema to IVocabulary."""
        items = [(item.value, item.title, item) for item in schema.items]
        items.sort()
        items = [(title, value) for sortkey, title, value in items]
        return SimpleVocabulary.fromItems(items)
    return factory

# DB Schema Vocabularies

SubscriptionVocabulary = vocab_factory(dbschema.BugSubscription)
BugStatusVocabulary = vocab_factory(dbschema.BugTaskStatus)
BugPriorityVocabulary = vocab_factory(dbschema.BugPriority)
BugSeverityVocabulary = vocab_factory(dbschema.BugSeverity)
BugRefVocabulary = vocab_factory(dbschema.BugExternalReferenceType)
InfestationStatusVocabulary = vocab_factory(dbschema.BugInfestationStatus)
PackagingTypeVocabulary = vocab_factory(dbschema.PackagingType)
TranslationPermissionVocabulary = vocab_factory(dbschema.TranslationPermission)
KarmaActionCategoryVocabulary = vocab_factory(dbschema.KarmaActionCategory)
TeamSubscriptionPolicyVocabulary = vocab_factory(
        dbschema.TeamSubscriptionPolicy)
GPGKeyAlgorithmVocabulary = vocab_factory(dbschema.GPGKeyAlgorithm)


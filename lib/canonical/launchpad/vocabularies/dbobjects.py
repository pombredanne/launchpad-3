
from zope.interface import implements
from zope.schema.interfaces import IVocabulary, IVocabularyTokenized
from zope.schema.vocabulary import SimpleTerm

from canonical.launchpad.database.person import Person
from canonical.launchpad.database.package import Sourcepackage, Binarypackage, \
                                         BinarypackageName
from canonical.launchpad.database.product import Product, ProductRelease
from canonical.launchpad.database.bug import BugTracker

__metaclass__ = type

# TODO: These vocabularies should limit their choices based on context (?)

class SQLObjectVocabularyBase(object):
    """A base class for widgets that are rendered to collect values
    for attributes that are SQLObjects, e.g. ForeignKey.

    So if a content class behind some form looks like:

    class Foo(SQLObject):
        id = IntCol(...)
        bar = ForeignKey(...)
        ...

    Then the vocabulary for the widget that captures a value for bar
    should derive from SQLObjectVocabularyBase.
    """
    implements(IVocabulary, IVocabularyTokenized)
    _orderBy = None

    def __init__(self, context):
        self.context = context

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.id, obj.title)

    def __iter__(self):
        params = {}
        if self._orderBy:
            params['orderBy'] = self._orderBy
        for obj in self._table.select(**params):
            yield self._toTerm(obj)

    def __len__(self):
        return len(iter(self))

    def __contains__(self, key):
        try:
            objs = list(self._table.select(self._table.q.id == int(key.id)))
            if len(objs) > 0:
                return True
        except ValueError:
            pass
        return False

    def getQuery(self):
        return None

    def getTerm(self, value):
        try:
            objs = list(self._table.select(self._table.q.id==int(value)))
        except ValueError:
            raise LookupError, value
        if len(objs) == 0:
            raise LookupError, value
        return self._toTerm(objs[0])

    def getTermByToken(self, token):
        return self.getTerm(token)


class SourcepackageVocabulary(SQLObjectVocabularyBase):
    # XXX: 2004/10/06 Brad Bollenbach -- may be broken, but there's
    # no test data for me to check yet. This'll be fixed by the end
    # of the week (2004/10/08) as we get Malone into usable shape.
    _table = Sourcepackage
    _orderBy = 'id'

    def _toTerm(self, obj):
        name = obj.sourcepackagename.name
        return SimpleTerm(obj.id, str(obj.id), name)
    def getTermByToken(self, token):
        return self.getTerm(token)


class BinarypackageNameVocabulary(SQLObjectVocabularyBase):
    _table = BinarypackageName
    _orderBy = 'name'

    def _toTerm(self, obj):
        return SimpleTerm(obj.id, obj.name, obj.name)

    def getTermByToken(self, token):
        return self.getTerm(token)



class ProductVocabulary(SQLObjectVocabularyBase):
    _table = Product

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.id, obj.displayname or obj.title)

# We cannot refer to a Binarypackage unambiguously by a name, as
# we have no assurace that a generated name using $BinarypackageName.name
# and $Binarypackage.version will be unique
# TODO: The edit sourcepackagebugassignment for does not default its
# binary package field
class BinarypackageVocabulary(SQLObjectVocabularyBase):
    # XXX: 2004/10/06 Brad Bollenbach -- may be broken, but there's
    # no test data for me to check yet. This'll be fixed by the end
    # of the week (2004/10/08) as we get Malone into usable shape.
    _table = Binarypackage
    _orderBy = 'id'

    def _toTerm(self, obj):
        return SimpleTerm(obj.id, str(obj.id), obj.title)

    def getTermByToken(self, token):
        return self.getTerm(token)

class BugTrackerVocabulary(SQLObjectVocabularyBase):
    # XXX: 2004/10/06 Brad Bollenbach -- may be broken, but there's
    # no test data for me to check yet. This'll be fixed by the end
    # of the week (2004/10/08) as we get Malone into usable shape.
    _table = BugTracker

class PersonVocabulary(SQLObjectVocabularyBase):
    _table = Person
    _orderBy = 'familyname'

    def _toTerm(self, obj):
        return SimpleTerm(
                obj, obj.id, obj.displayname or '%s %s' % (
                    obj.givenname, obj.familyname))

class ProductReleaseVocabulary(SQLObjectVocabularyBase):
    _table = ProductRelease
    _orderBy = 'product'

    def _toTerm(self, obj):
        return SimpleTerm(
            obj, obj.id, obj.product.name + " " + obj.version)



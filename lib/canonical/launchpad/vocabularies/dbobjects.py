'''
Vocabularies pulling stuff from the database.

You probably don't want to use these classes directly - see the
docstring in __init__.py for details
'''
from zope.interface import implements, Interface
from zope.schema.interfaces import IVocabulary, IVocabularyTokenized
from zope.schema.vocabulary import SimpleTerm
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.database.person import Person
from canonical.launchpad.database.sourcepackage import SourcePackage, \
                                            SourcePackageRelease
from canonical.launchpad.database.binarypackage import BinaryPackage, \
                                            BinaryPackageName
from canonical.launchpad.database.product import Product
from canonical.launchpad.database.productrelease import ProductRelease
from canonical.launchpad.database.bugtracker import BugTracker
from canonical.database.sqlbase import SQLBase, quote_like


class IHugeVocabulary(IVocabulary):
    """Interface for huge vocabularies.
    
    Items in an IHugeVocabulary should have human readable tokens or the
    default UI will suck.

    """
    def search(query=None):
        """Return an iterable of ITokenizedTerm that match the
        search string.

        Note that what is searched and how the match is the choice of the 
        IHugeVocabulary implementation.
        """

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
        return len(list(iter(self)))

    def __contains__(self, obj):
        try:
            objs = list(self._table.select(self._table.q.id == obj.id))
            if len(objs) > 0:
                return True
        except ValueError:
            pass
        return False

    def getQuery(self):
        return None

    def getTerm(self, value):
        # Short circuit. There is probably a design problem here since we
        # sometimes get the id and sometimes an SQLBase instance.
        if isinstance(removeSecurityProxy(value), SQLBase):
            return self._toTerm(value)

        try:
            int(value)
        except:
            import pdb; pdb.set_trace()
            raise RuntimeError, 'Got a %r' % (value,)

        try:
            objs = list(self._table.select(self._table.q.id==int(value)))
        except ValueError:
            raise LookupError, value
        if len(objs) == 0:
            raise LookupError, value
        return self._toTerm(objs[0])

    def getTermByToken(self, token):
        return self.getTerm(token)


class SourcePackageVocabulary(SQLObjectVocabularyBase):
    _table = SourcePackage
    _orderBy = 'id'

    implements(IHugeVocabulary)

    def _toTerm(self, obj):
        name = obj.sourcepackagename.name
        return SimpleTerm(obj, str(obj.id), name)

    def getTermByToken(self, token):
        return self.getTerm(token)

    def search(self, query):
        '''Returns products where the sourcepackage name starts with the given
        query. Returns an empty list if query is None or an empty string.

        We don't do a proper substring match, as this will be slow because
        PostgreSQL cannot do this search using an index.

        '''
        if not query:
            query = ''
            #return []
        #import pdb; pdb.set_trace()
        t = self._table
        objs = [self._toTerm(r)
            for r in t.select('''
                sourcepackage.sourcepackagename = sourcepackagename.id
                AND sourcepackagename.name like %s || '%%'
                ''' % quote_like(query.lower()),
                    #t.q.sourcepackagename.name.startswith(query.lower()),
                    ['SourcePackageName']
                    )
            ]
        return objs


class BinaryPackageNameVocabulary(SQLObjectVocabularyBase):
    _table = BinaryPackageName
    _orderBy = 'name'

    def _toTerm(self, obj):
        return SimpleTerm(obj.id, obj.name, obj.name)

    def getTermByToken(self, token):
        return self.getTerm(token)



class ProductVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)
    _table = Product

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.title)

    def getTermByToken(self, token):
        tab = self._table
        try:
            objs = list(tab.select(tab.q.name == token))
        except ValueError:
            objs = ()
        if len(objs) != 1:
            raise LookupError, token
        return self._toTerm(objs[0])

    def search(self, query):
        '''Returns products where the product name starts with the given
        query. Returns an empty list if query is None or an empty string.

        We don't do a proper substring match, as this will be slow because
        PostgreSQL cannot do this search using an index.

        '''
        if not query:
            return []
        t = self._table
        objs = [self._toTerm(r)
            for r in t.select(t.q.name.startswith(query.lower()))
            ]
        return objs

# We cannot refer to a BinaryPackage unambiguously by a name, as
# we have no assurace that a generated name using $BinaryPackageName.name
# and $BinaryPackage.version will be unique
# TODO: The edit sourcepackagebugassignment for does not default its
# binary package field
class BinaryPackageVocabulary(SQLObjectVocabularyBase):
    # XXX: 2004/10/06 Brad Bollenbach -- may be broken, but there's
    # no test data for me to check yet. This'll be fixed by the end
    # of the week (2004/10/08) as we get Malone into usable shape.
    _table = BinaryPackage
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

    def __iter__(self):
        kw = {}
        if self._orderBy:
            kw['orderBy'] = self._orderBy
        for obj in self._table.select('password IS NOT NULL', **kw):
            yield self._toTerm(obj)

    def __contains__(self, obj):
        try:
            objs = list(self._table.select(self._table.q.id == obj.id))
            if len(objs) > 0:
                return True
        except ValueError:
            pass
        return False




class ProductReleaseVocabulary(SQLObjectVocabularyBase):
    _table = ProductRelease
    _orderBy = 'product'

    def _toTerm(self, obj):
        return SimpleTerm(
            obj, obj.id, obj.product.name + " " + obj.version)

class PackageReleaseVocabulary(SQLObjectVocabularyBase):
    _table = SourcePackageRelease
    _orderBy = 'sourcepackage'

    def _toTerm(self, obj):
        return SimpleTerm(
            obj, obj.id, obj.sourcepackage.name + " " + obj.version)

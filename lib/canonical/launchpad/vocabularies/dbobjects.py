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
from canonical.database.sqlbase import SQLBase, quote_like, quote

from sqlobject import AND, OR, CONTAINSSTRING


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
            objs = list(self._table.select(self._table.q.id == int(obj)))
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
            value = int(value)
        except ValueError:
            raise LookupError, value

        try:
            objs = list(self._table.select(self._table.q.id==value))
        except ValueError:
            raise LookupError, value
        if len(objs) == 0:
            raise LookupError, value
        return self._toTerm(objs[0])

    def getTermByToken(self, token):
        return self.getTerm(token)


class SourcePackageVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)

    _table = SourcePackage
    _orderBy = 'id'

    def _toTerm(self, obj):
        name = obj.sourcepackagename.name
        return SimpleTerm(obj, str(obj.id), name)

    def getTermByToken(self, token):
        return self.getTerm(token)

    def search(self, query):
        '''Returns products where the sourcepackage name contains the given
        query. Returns an empty list if query is None or an empty string.

        This won't use indexes. If this is too slow, we need full text
        searching.

        '''
        if not query:
            return []
        query = query.lower()
        t = self._table
        objs = [self._toTerm(r)
            for r in t.select('''
                sourcepackage.sourcepackagename = sourcepackagename.id
                AND (
                    sourcepackagename.name like '%%' || %s || '%%'
                    OR sourcepackage.fti @@ ftq(%s)
                    )
                ''' % (quote_like(query), quote(query)),
                ['SourcePackageName']
                )
            ]
        return objs

class NamedSQLObjectVocabulary(SQLObjectVocabularyBase):
    '''A SQLObjectVocabulary base for database tables that have a unique
        name column.
        
        Provides all methods required by IHugeVocabulary,
        although it doesn't actually specify this interface since it may
        not actually be huge and require the custom widgets.

        May still want to override _toTerm to provide a nicer title
        and search to search on titles or descriptions.
    '''
    _orderBy = 'name'

    def _toTerm(self, obj):
        return SimpleTerm(obj.id, obj.name, obj.name)

    def getTermByToken(self, token):
        objs = list(self._table.selectBy(name=token))
        if not objs:
            raise LookupError, token
        return self._toTerm(objs[0])

    def search(self, query):
        '''Return terms where query is a subtring of the name'''
        if not query:
            return []
        objs = self._table.select(
            CONTAINSSTRING(self._table.q.name, query)
            )
        return [self._toTerm(obj) for obj in objs]


class BinaryPackageNameVocabulary(NamedSQLObjectVocabulary):
    implements(IHugeVocabulary)

    _table = BinaryPackageName
    _orderBy = 'name'


class ProductVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)
    _table = Product

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.title)

    def getTermByToken(self, token):
        objs = self._table.select(self._table.q.name == token)
        if len(objs) != 1:
            raise LookupError, token
        return self._toTerm(objs[0])

    def search(self, query):
        '''Returns products where the product name, displayname, title,
        shortdesc, or description contain the given query. Returns an empty list
        if query is None or an empty string.

        Note that this cannot use an index - if it is too slow we need
        full text searching.

        '''
        if query:
            query = query.lower()
            like_query = quote('%%%s%%' % quote_like(query)[1:-1])
            fti_query = quote(query)
            sql = "fti @@ ftq(%s)" % fti_query
            return [self._toTerm(r) for r in self._table.select(sql)]

        return []

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

class PersonVocabulary(NamedSQLObjectVocabulary):
    implements(IHugeVocabulary)
    _table = Person
    _orderBy = 'familyname'

    def _toTerm(self, obj):
        return SimpleTerm(
                obj, obj.name, obj.displayname or '%s %s' % (
                    obj.givenname, obj.familyname))

    def search(self, query):
        '''Return terms where query is a subtring of the name'''
        # TODO: This may actually be fast enough, or perhaps we will
        # need to implement full text search inside PostgreSQL (tsearch or
        # similar) -- StuartBishop 2004/11/24
        if not query:
            return []
        kw = {}
        if self._orderBy:
            kw['orderBy'] = self._orderBy
        query = query.lower()
        like_query = quote('%%%s%%' % quote_like(query)[1:-1])
        fti_query = quote(query)
        objs = self._table.select(
            "name LIKE %s OR fti @@ ftq(%s)" % (like_query, fti_query), **kw
            )
        return [self._toTerm(obj) for obj in objs]


class ValidPersonVocabulary(PersonVocabulary):
    def __iter__(self):
        kw = {}
        if self._orderBy:
            kw['orderBy'] = self._orderBy
        for obj in self._table.select('password IS NOT NULL', **kw):
            yield self._toTerm(obj)

    def __contains__(self, obj):
        objs = list(self._table.select(AND(
            self._table.q.id == int(obj),
            self._table.q.password is not None
            )))
        return len(objs) > 0

    def search(self, query):
        '''Return terms where query is a subtring of the name'''
        # TODO: This may actually be fast enough, or perhaps we will
        # need to implement full text search inside PostgreSQL (tsearch or
        # similar) -- StuartBishop 2004/11/24
        if not query:
            return []
        query = query.lower()
        like_query = quote('%%%s%%' % quote_like(query)[1:-1])
        fti_query = quote(query)
        kw = {}
        if self._orderBy:
            kw['orderBy'] = self._orderBy
        objs = self._table.select('''
            password IS NOT NULL
            AND (name LIKE %s OR fti @@ ftq(%s))
            ''' % (like_query, fti_query), **kw
            )
        return [self._toTerm(obj) for obj in objs]

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

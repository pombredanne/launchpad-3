"""
Vocabularies pulling stuff from the database.

You probably don't want to use these classes directly - see the
docstring in __init__.py for details
"""
from zope.interface import implements, Interface
from zope.schema.interfaces import IVocabulary, IVocabularyTokenized
from zope.schema.vocabulary import SimpleTerm
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.database import Distribution
from canonical.launchpad.database import DistroRelease
from canonical.launchpad.database import Person
from canonical.launchpad.database import GPGKey
from canonical.launchpad.database import SourcePackage, \
    SourcePackageRelease, SourcePackageName
from canonical.launchpad.database import BinaryPackage
from canonical.launchpad.database import BinaryPackageName
from canonical.launchpad.database import Milestone
from canonical.launchpad.database import Product
from canonical.launchpad.database import Project
from canonical.launchpad.database import ProductRelease
from canonical.launchpad.database import BugTracker
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

    def __init__(self, context=None):
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

class NamedSQLObjectVocabulary(SQLObjectVocabularyBase):
    """A SQLObjectVocabulary base for database tables that have a unique
        name column.
        
        Provides all methods required by IHugeVocabulary,
        although it doesn't actually specify this interface since it may
        not actually be huge and require the custom widgets.

        May still want to override _toTerm to provide a nicer title
        and search to search on titles or descriptions.
    """
    _orderBy = 'name'

    def _toTerm(self, obj):
        return SimpleTerm(obj.id, obj.name, obj.name)

    def getTermByToken(self, token):
        objs = list(self._table.selectBy(name=token))
        if not objs:
            raise LookupError, token
        return self._toTerm(objs[0])

    def search(self, query):
        """Return terms where query is a subtring of the name"""
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
    _orderBy = 'displayname'

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.title)

    def getTermByToken(self, token):
        objs = self._table.select(self._table.q.name == token)
        if objs.count() != 1:
            raise LookupError, token
        return self._toTerm(objs[0])

    def search(self, query):
        """Returns products where the product name, displayname, title,
        shortdesc, or description contain the given query. Returns an empty list
        if query is None or an empty string.

        Note that this cannot use an index - if it is too slow we need
        full text searching.

        """
        if query:
            query = query.lower()
            like_query = quote('%%%s%%' % quote_like(query)[1:-1])
            fti_query = quote(query)
            sql = "fti @@ ftq(%s)" % fti_query
            return [self._toTerm(r) for r in self._table.select(sql, orderBy=self._orderBy)]

        return []

class ProjectVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)
    _table = Project
    _orderBy = 'displayname'

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.title)

    def getTermByToken(self, token):
        objs = self._table.select(self._table.q.name == token)
        if len(objs) != 1:
            raise LookupError, token
        return self._toTerm(objs[0])

    def search(self, query):
        """Returns projects where the project name, displayname, title,
        shortdesc, or description contain the given query. Returns an empty list
        if query is None or an empty string.

        Note that this cannot use an index - if it is too slow we need
        full text searching.

        """
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
# TODO: The edit ibugtask form does not default its
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
    _orderBy = ['familyname','givenname','displayname']

    def _toTerm(self, obj):
        return SimpleTerm(
                obj, obj.name, obj.displayname or '%s %s' % (
                    obj.givenname, obj.familyname))

    def search(self, query):
        """Return terms where query is a subtring of the name"""
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


class ValidOwnerVocabulary(PersonVocabulary):
    """
    ValidOwnerVocabulary implements a Vocabulary Describing valid Owner
    entities, People and Teams, according the Ubuntu Membership
    Management System.
    """
    ## XXX cprov 20050124
    ## Waiting for the FOAF support to follow implementation path.
    pass


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
        """Return terms where query is a subtring of the name"""
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
        objs = self._table.select("""
            password IS NOT NULL
            AND (name LIKE %s OR fti @@ ftq(%s))
            """ % (like_query, fti_query), **kw
            )
        return [self._toTerm(obj) for obj in objs]

class ProductReleaseVocabulary(SQLObjectVocabularyBase):
    _table = ProductRelease
    _orderBy = 'product'

    def _toTerm(self, obj):
        return SimpleTerm(
            obj, obj.id, obj.product.name + " " + obj.version)

class MilestoneVocabulary(NamedSQLObjectVocabulary):
    _table = Milestone
    _orderBy = 'name'

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.name)

    def __iter__(self):
        if self.context.product:
            for ms in self.context.product.milestones:
                yield SimpleTerm(ms, ms.name, ms.name)

class PackageReleaseVocabulary(SQLObjectVocabularyBase):
    _table = SourcePackageRelease
    _orderBy = 'id'

    def _toTerm(self, obj):
        return SimpleTerm(
            obj, obj.id, obj.name + " " + obj.version)

class SourcePackageNameVocabulary(NamedSQLObjectVocabulary):
    implements(IHugeVocabulary)

    _table = SourcePackageName
    _orderBy = 'name'

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.name)

    def search(self, query):
        """Returns names where the sourcepackage contains the given
        query. Returns an empty list if query is None or an empty string.

        """
        if not query:
            return []
        query = query.lower()
        t = self._table
        objs = [self._toTerm(r)
                   for r in t.select("""
                       sourcepackagename.name like '%%' || %s || '%%'
                       """ % quote_like(query))]
        return objs


class DistributionVocabulary(NamedSQLObjectVocabulary):
    implements(IHugeVocabulary)

    _table = Distribution
    _orderBy = 'name'

    def search(self, query):
        """Return terms where query is a substring of the name"""
        if query:
            query = query.lower()
            like_query = quote('%%%s%%' % quote_like(query)[1:-1])
            fti_query = quote(query)
            kw = {}
            if self._orderBy:
                kw['orderBy'] = self._orderBy
            objs = self._table.select("name LIKE %s" % like_query, **kw)
            return [self._toTerm(obj) for obj in objs]

        return []


class ValidGPGKeyVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)
    
    _table = GPGKey
    _orderBy = 'keyid'

    def _toTerm(self, obj):
        return SimpleTerm(
            obj, obj.id, obj.owner.displayname + " " + obj.keyid)


    def search(self, query):
        """Return terms where query is a substring of the keyid"""
        if query:
            clauseTables = ['Person',]

            query = quote(query.lower())

            objs = self._table.select(("GPGKey.owner = Person.id AND "
                                       "Person.fti @@ ftq(%s)" % query),
                                      orderBy=self._orderBy,
                                      clauseTables=clauseTables)
            
            return [self._toTerm(obj) for obj in objs]

        return []


class DistroReleaseVocabulary(NamedSQLObjectVocabulary):
    implements(IHugeVocabulary)

    _table = DistroRelease
    _orderBy = 'name'

    def search(self, query):
        """Return terms where query is a substring of the name"""
        if query:
            query = query.lower()
            like_query = quote('%%%s%%' % quote_like(query)[1:-1])
            fti_query = quote(query)
            kw = {}
            if self._orderBy:
                kw['orderBy'] = self._orderBy
            objs = self._table.select("name LIKE %s" % like_query, **kw)
            return [self._toTerm(obj) for obj in objs]

        return []


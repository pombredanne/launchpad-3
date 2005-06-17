# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Vocabularies pulling stuff from the database.

You probably don't want to use these classes directly - see the
docstring in __init__.py for details.
"""

__metaclass__ = type

from zope.component import getUtility
from zope.interface import implements, Interface
from zope.schema.interfaces import IVocabulary, IVocabularyTokenized
from zope.schema.vocabulary import SimpleTerm
from zope.security.proxy import removeSecurityProxy

from sqlobject import AND, OR, CONTAINSSTRING, SQLObjectMoreThanOneResultError

from canonical.lp.dbschema import EmailAddressStatus
from canonical.database.sqlbase import SQLBase, quote_like, quote, sqlvalues
from canonical.launchpad.database import (
    Distribution, DistroRelease, Person, GPGKey, SourcePackage,
    SourcePackageRelease, SourcePackageName, BinaryPackage, BugWatch,
    BinaryPackageName, BugTracker, Language, Milestone, Product,
    Project, ProductRelease, ProductSeries, TranslationGroup, BugTracker,
    POTemplateName, EmailAddress)
from canonical.launchpad.interfaces import ILaunchBag, ITeam

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

class SQLObjectVocabularyBase:
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

    Provides all methods required by IHugeVocabulary, although it
    doesn't actually specify this interface since it may not actually
    be huge and require the custom widgets.

    May still want to override _toTerm to provide a nicer title and
    search to search on titles or descriptions.
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
        if query:
            objs = self._table.select(
                CONTAINSSTRING(self._table.q.name, query)
                )
            for o in objs:
                yield self._toTerm(o)


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
        obj = self._table.selectOne(self._table.q.name == token)
        if obj is None:
            raise LookupError, token
        return self._toTerm(obj)

    def search(self, query):
        """Returns products where the product name, displayname, title,
        summary, or description contain the given query. Returns an empty list
        if query is None or an empty string.

        Note that this cannot use an index - if it is too slow we need
        full text searching.

        """
        if query:
            query = query.lower()
            like_query = "'%%' || %s || '%%'" % quote_like(query)
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
        summary, or description contain the given query. Returns an empty list
        if query is None or an empty string.

        Note that this cannot use an index - if it is too slow we need
        full text searching.

        """
        if query:
            query = query.lower()
            like_query = "'%%' || %s || '%%'" % quote_like(query)
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


class LanguageVocabulary(SQLObjectVocabularyBase):
    _table = Language
    _orderBy = 'englishname'

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.id, obj.displayname)


class TranslationGroupVocabulary(NamedSQLObjectVocabulary):
    _table = TranslationGroup

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.title)


class PersonVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)
    _orderBy = ['familyname','givenname','displayname', 'name']
    _table = Person

    def _toTerm(self, obj):
        """Return the term for this object.

        Preference is given to email-based terms, falling back on
        name-based terms when no preferred email exists for the
        IPerson.
        """
        if obj.preferredemail is not None:
            return SimpleTerm(obj, obj.preferredemail.email, obj.browsername)
        else:
            return SimpleTerm(obj, obj.name, obj.browsername)

    def getTermByToken(self, token):
        """Return the term for the given token.

        If the token contains an '@', treat it like an
        email. Otherwise, treat it like a name.
        """
        if "@" in token:
            # This looks like an email token, so let's do an object
            # lookup based on that.
            try:
                email = EmailAddress.selectOneBy(email=token)
            except SQLObjectMoreThanOneResultError:
                raise LookupError, token

            return self._toTerm(email.person)
        else:
            # This doesn't look like an email, so let's simply treat
            # it like a name.
            person = Person.selectOneBy(name=token)
            return self._toTerm(person)

    def search(self, query):
        """Return terms where query is a subtring of the name"""
        if query:
            kw = {'clauseTables' : ["emailaddress"]}
            if self._orderBy:
                kw['orderBy'] = self._orderBy
            query = query.lower()
            like_query = "'%%' || %s || '%%'" % quote_like(query)
            fti_query = quote(query)
            objs = Person.select("""
                (name LIKE %s OR fti @@ ftq(%s)) AND
                person.id = emailaddress.person AND
                emailaddress.status = %d
                """ % (like_query, fti_query,
                       EmailAddressStatus.PREFERRED.value),
                **kw)

            return [self._toTerm(obj) for obj in objs]


class ValidPersonOrTeamVocabulary(PersonVocabulary):
    """The set of valid Persons/Teams in Launchpad.

    A Person is considered valid if he have at least one validated email
    address, a password set and Person.merged is None. Teams have no
    restrictions at all, which means that all teams are considered valid.

    This vocabulary is registered as ValidPersonOrTeam, ValidAssignee,
    ValidMaintainer and ValidOwner, because they have exactly the same
    requisites.
    """

    _validpersons = ("""
        teamowner IS NULL AND password IS NOT NULL AND merged IS NULL AND
        emailaddress.person = person.id AND
        emailaddress.status = %d
        """ % EmailAddressStatus.PREFERRED.value)
    _validteams = ("""
        teamowner IS NOT NULL AND
        person.id = emailaddress.person AND
        emailaddress.status = %d
        """ % EmailAddressStatus.PREFERRED.value)

    _basequery = '(%s) OR (%s)' % (_validpersons, _validteams)

    def _select(self, query):
        return Person.select(
            query, orderBy=self._orderBy,
            clauseTables=["emailaddress"],
            distinct=True)

    def __iter__(self):
        for obj in self._select(self._basequery):
            yield self._toTerm(obj)

    def __contains__(self, obj):
        # XXX: salgado, 2005-05-09: Soon we'll be able to say: "obj in
        # self._table.select(self._basequery)" and I'll fix this method.
        query = '(%s) AND (person.id = %d)' % (self._basequery, obj.id)
        return bool(self._select(query).count())

    def search(self, text):
        """Return persons where <text> is a subtring of either the name,
        givenname, familyname or displayname.
        """
        if not text:
            return []
        text = text.lower()
        like_query = "'%%' || %s || '%%'" % quote_like(text)
        fti_query = quote(text)
        query = ("(%s) AND (name LIKE %s OR fti @@ ftq(%s))" % (
            self._basequery, like_query, fti_query))
        return [self._toTerm(obj) for obj in self._select(query)]


class ValidTeamOwnerVocabulary(ValidPersonOrTeamVocabulary):
    """The set of Persons/Teams that can be owner of a team.

    With the exception of the team itself and all teams owned by that team,
    all valid persons and teams are valid owners for the team.
    """

    def __init__(self, context):
        if not context:
            raise ValueError('ValidTeamOwnerVocabulary needs a context.')
        if not ITeam.providedBy(context):
            raise ValueError(
                    "ValidTeamOwnerVocabulary's context must be a team.")
        ValidPersonOrTeamVocabulary.__init__(self, context)
        extraclause = ('''
            (person.teamowner != %d OR person.teamowner IS NULL) AND
            person.id != %d''' % (context.id, context.id))
        self._basequery = '(%s) AND (%s)' % (self._basequery, extraclause)


class ProductReleaseVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)

    _table = ProductRelease
    # XXX carlos Perello Marin 2005-05-16:
    # Sorting by version won't give the expected results, because it's just a
    # text field.  e.g. ["1.0", "2.0", "11.0"] would be sorted as ["1.0",
    # "11.0", "2.0"].
    # See https://launchpad.ubuntu.com/malone/bugs/687
    _orderBy = [Product.q.name, ProductSeries.q.name,
                ProductRelease.q.version]
    _clauseTables = ['Product', 'ProductSeries']

    def __iter__(self):
        for obj in self._table.select(
            ProductRelease.q.productseries == ProductSeries.q.id,
            ProductSeries.q.productID == Product.q.id,
            orderBy=self._orderBy,
            clauseTables=self._clauseTables,
            ):
            yield self._toTerm(obj)

    def _toTerm(self, obj):
        productrelease = obj
        productseries = productrelease.productseries
        product = productseries.product

        # NB: We use '/' as the seperator because '-' is valid in
        # a product.name or productseries.name
        token = '%s/%s/%s' % (
                    product.name, productseries.name, productrelease.version)
        return SimpleTerm(
            obj.id, token, '%s %s %s' % (
                product.name, productseries.name, productrelease.version))

    def getTermByToken(self, token):
        try:
            productname, productseriesname, productreleaseversion = \
                token.split('/', 2)
        except ValueError:
            raise LookupError, token

        obj = ProductRelease.selectOne(AND(Product.q.name == productname,
                ProductSeries.q.name == productseriesname,
                ProductRelease.q.version == productreleaseversion
                ))
        try:
            return self._toTerm(obj)
        except IndexError:
            raise LookupError, token

    def search(self, query):
        """Return terms where query is a substring of the version or name"""
        if query:
            query = query.lower()
            objs = self._table.select(
                AND(
                    ProductSeries.q.id == ProductRelease.q.productseriesID,
                    Product.q.id == ProductSeries.q.productID,
                    OR(
                        CONTAINSSTRING(Product.q.name, query),
                        CONTAINSSTRING(ProductSeries.q.name, query),
                        CONTAINSSTRING(ProductRelease.q.version, query)
                        )
                    ),
                orderBy=self._orderBy
                )

            for o in objs:
                yield self._toTerm(o)


class ProductSeriesVocabulary(SQLObjectVocabularyBase):
    implements(IHugeVocabulary)

    _table = ProductSeries
    _orderBy = [Product.q.name, ProductSeries.q.name]
    _clauseTables = ['Product']

    def __iter__(self):
        for obj in self._table.select(
                ProductSeries.q.productID == Product.q.id,
                orderBy=self._orderBy,
                clauseTables=self._clauseTables,
                ):
            yield self._toTerm(obj)

    def _toTerm(self, obj):
        # NB: We use '/' as the seperator because '-' is valid in
        # a product.name or productseries.name
        token = '%s/%s' % (obj.product.name, obj.name)
        return SimpleTerm(obj.id,
                          token,
                          obj.product.name + ' ' + obj.name)

    def getTermByToken(self, token):
        try:
            productname, productseriesname = token.split('/', 1)
        except ValueError:
            raise LookupError, token

        objs = ProductSeries.select(AND(Product.q.name == productname,
                ProductSeries.q.name == productseriesname
                ))
        try:
            return self._toTerm(objs[0])
        except IndexError:
            raise LookupError, token

    def search(self, query):
        """Return terms where query is a substring of the name"""
        if query:
            query = query.lower()
            objs = self._table.select(
                    AND(
                        Product.q.id == ProductSeries.q.productID,
                        OR(
                            CONTAINSSTRING(Product.q.name, query),
                            CONTAINSSTRING(ProductSeries.q.name, query)
                            )
                        ),
                    orderBy=self._orderBy
                    )
            for o in objs:
                yield self._toTerm(o)

class FilteredProductSeriesVocabulary(SQLObjectVocabularyBase):
    """Describes ProductSeries of a particular product."""
    _table = ProductSeries
    _orderBy = 'product'

    def _toTerm(self, obj):
        return SimpleTerm(
            obj, obj.id, obj.product.name + " " + obj.name)

    def __iter__(self):
        kw = {}
        if self._orderBy:
            kw['orderBy'] = self._orderBy
        if self.context.product:
            product = self.context.product
            for series in self._table.selectBy(productID=product.id, **kw):
                yield self._toTerm(series)


class MilestoneVocabulary(NamedSQLObjectVocabulary):
    _table = Milestone
    _orderBy = 'name'

    def _toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.name)

    def __iter__(self):
        product = getUtility(ILaunchBag).product
        if product is None:
            product = self.context.product

        if product is not None:
            for ms in product.milestones:
                yield SimpleTerm(ms, ms.name, ms.name)

class BugWatchVocabulary(SQLObjectVocabularyBase):
    _table = BugWatch

    def __iter__(self):
        bug = getUtility(ILaunchBag).bug
        if bug is None:
            raise ValueError, 'Unknown bug context for Watch list.'

        for watch in bug.watches:
            yield self._toTerm(watch)

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
            like_query = "'%%' || %s || '%%'" % quote_like(query)
            fti_query = quote(query)
            kw = {}
            if self._orderBy:
                kw['orderBy'] = self._orderBy
            objs = self._table.select("name LIKE %s" % like_query, **kw)
            return [self._toTerm(obj) for obj in objs]

        return []


class DistroReleaseVocabulary(NamedSQLObjectVocabulary):
    implements(IHugeVocabulary)

    _table = DistroRelease
    _orderBy = [Distribution.q.name, DistroRelease.q.name]
    _clauseTables = ['Distribution']

    def __iter__(self):
        for obj in self._table.select(
                DistroRelease.q.distributionID == Distribution.q.id,
                orderBy=self._orderBy,
                clauseTables=self._clauseTables,
                ):
            yield self._toTerm(obj)

    def _toTerm(self, obj):
        # NB: We use '/' as the seperater because '-' is valid in
        # a distribution.name
        token = '%s/%s' % (obj.distribution.name, obj.name)
        return SimpleTerm(obj.id, token, obj.title)

    def getTermByToken(self, token):
        try:
            distroname, distroreleasename = token.split('/', 1)
        except ValueError:
            raise LookupError, token

        obj = DistroRelease.selectOne(AND(Distribution.q.name == distroname,
            DistroRelease.q.name == distroreleasename))
        if obj is None:
            raise LookupError, token
        else:
            return self._toTerm(obj)

    def search(self, query):
        """Return terms where query is a substring of the name."""
        if query:
            query = query.lower()
            objs = self._table.select(
                    AND(
                        Distribution.q.id == DistroRelease.q.distributionID,
                        OR(
                            CONTAINSSTRING(Distribution.q.name, query),
                            CONTAINSSTRING(DistroRelease.q.name, query)
                            )
                        ),
                    orderBy=self._orderBy
                    )
            for o in objs:
                yield self._toTerm(o)


class POTemplateNameVocabulary(NamedSQLObjectVocabulary):
    implements(IHugeVocabulary)

    _table = POTemplateName
    _orderBy = 'name'

    def search(self, query):
        """Return terms where query is a substring of the name"""
        if query:
            query = query.lower()
            objs = self._table.select(
                CONTAINSSTRING(POTemplateName.q.name, query),
                orderBy=self._orderBy
                )

            for o in objs:
                yield self._toTerm(o)

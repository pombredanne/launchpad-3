# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

"""FAQ document models."""

__metaclass__ = type

__all__ = [
    'FAQ',
    'FAQSearch',
    'FAQSet',
    ]

from sqlobject import (
    ForeignKey, SQLMultipleJoin, SQLObjectNotFound, StringCol)
from sqlobject.sqlbuilder import SQLConstant

from zope.event import notify
from zope.interface import implements

from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.nl_search import nl_phrase_search
from canonical.database.sqlbase import quote, SQLBase, sqlvalues

from canonical.launchpad.event import SQLObjectCreatedEvent
from canonical.launchpad.interfaces import (
    IDistribution, IFAQ, IFAQSet, FAQSort, IPerson, IProduct, IProject)
from canonical.launchpad.validators.person import validate_public_person


class FAQ(SQLBase):
    """See `IFAQ`."""

    implements(IFAQ)

    _table = 'FAQ'
    _defaultOrder = ['date_created', 'id']

    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)

    title = StringCol(notNull=True)

    keywords = StringCol(dbName="tags", notNull=False, default=None)

    content = StringCol(notNull=False, default=None)

    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)

    last_updated_by = ForeignKey(
        dbName='last_updated_by', foreignKey='Person',
        storm_validator=validate_public_person, notNull=False,
        default=None)

    date_last_updated = UtcDateTimeCol(notNull=False, default=None)

    product = ForeignKey(
        dbName='product', foreignKey='Product', notNull=False, default=None)

    distribution = ForeignKey(
        dbName='distribution', foreignKey='Distribution', notNull=False,
        default=None)

    related_questions = SQLMultipleJoin(
        'Question', joinColumn='faq', orderBy=['Question.datecreated'])

    @property
    def target(self):
        """See `IFAQ`."""
        if self.product:
            return self.product
        else:
            return self.distribution

    @staticmethod
    def new(owner, title, content, keywords=keywords, date_created=None,
            product=None, distribution=None):
        """Factory method to create a new FAQ.

        Ensure that only one of product or distribution is given.
        """
        if not IPerson.providedBy(owner):
            raise AssertionError(
                'owner parameter should be an IPerson, not %s' % type(owner))
        if product is not None and distribution is not None:
            raise AssertionError(
                "only one of product or distribution should be provided")
        if product is None and distribution is None:
            raise AssertionError("product or distribution must be provided")
        if date_created is None:
            date_created = DEFAULT
        faq = FAQ(
            owner=owner, title=title, content=content, keywords=keywords,
            date_created=date_created, product=product,
            distribution=distribution)
        notify(SQLObjectCreatedEvent(faq))
        return faq

    @staticmethod
    def findSimilar(summary, product=None, distribution=None):
        """Return the FAQs similar to summary.

        See `IFAQTarget.findSimilarFAQs` for details.
        """
        assert not (product and distribution), (
            'only one of product or distribution should be provided')
        if product:
            target_constraint = 'product = %s' % sqlvalues(product)
        elif distribution:
            target_constraint = 'distribution = %s' % sqlvalues(distribution)
        else:
            raise AssertionError('must provide product or distribution')

        fti_search = nl_phrase_search(summary, FAQ, target_constraint)
        if not fti_search:
            # No useful words to search on in that summary.
            return FAQ.select('1 = 2')

        return FAQ.select(
            '%s AND FAQ.fti @@ %s' % (target_constraint, quote(fti_search)),
            orderBy=[
                SQLConstant("-rank(FAQ.fti, ftq(%s))" % quote(fti_search)),
                "-FAQ.date_created"])

    @staticmethod
    def getForTarget(id, target):
        """Return the FAQ with the requested id.

        When target is not None, the target will be checked to make sure
        that the FAQ is in the expected target or return None otherwise.
        """
        try:
            faq = FAQ.get(id)
            if target is None or target == faq.target:
                return faq
            else:
                return None
        except SQLObjectNotFound:
            return None


class FAQSearch:
    """Object that encapsulates a FAQ search.

    It is used to implement the `IFAQCollection`.searchFAQs() method.
    """
    search_text = None
    owner = None
    sort = None
    product = None
    distribution = None
    project = None

    def __init__(self, search_text=None, owner=None, sort=None, product=None,
                 distribution=None, project=None):
        """Initialize a new FAQ search.

        See `IFAQCollection`.searchFAQs for the basic parameters description.
        Additional parameters:
        :param product: The product in which to search for FAQs.
        :param distribution: The distribution in which to search for FAQs.
        :param project: The project in which to search for FAQs.
        """
        if search_text is not None:
            assert isinstance(search_text, basestring), (
                'search_text should be a string, not %s' % type(search_text))
            self.search_text = search_text

        if owner is not None:
            assert IPerson.providedBy(owner), (
                'owner should be an IPerson, not %s' % type(owner))
            self.owner = owner

        if sort is not None:
            assert sort in FAQSort.items, (
                'sort should be an item from FAQSort, not %s' % type(sort))
            self.sort = sort

        if product is not None:
            assert IProduct.providedBy(product), (
                'product should be an IProduct, not %s' % type(product))
            assert distribution is None and project is None, (
                'can only use one of product, distribution, or project')
            self.product = product

        if distribution is not None:
            assert IDistribution.providedBy(distribution), (
                'distribution should be an IDistribution, %s' %
                type(distribution))
            assert product is None and project is None, (
                'can only use one of product, distribution, or project')
            self.distribution = distribution

        if project is not None:
            assert IProject.providedBy(project), (
                'project should be an IProject, not %s' % type(project))
            assert product is None and distribution is None, (
                'can only use one of product, distribution, or project')
            self.project = project

    def getResults(self):
        """Return the FAQs matching this search."""
        return FAQ.select(
            self.getConstraints(),
            clauseTables=self.getClauseTables(),
            orderBy=self.getOrderByClause())

    def getConstraints(self):
        """Return the constraints to use by this search."""
        constraints = []

        if self.search_text:
            constraints.append('FAQ.fti @@ ftq(%s)' % quote(self.search_text))

        if self.owner:
            constraints.append('FAQ.owner = %s' % sqlvalues(self.owner))

        if self.product:
            constraints.append('FAQ.product = %s' % sqlvalues(self.product))

        if self.distribution:
            constraints.append(
                'FAQ.distribution = %s' % sqlvalues(self.distribution))

        if self.project:
            constraints.append(
                'FAQ.product = Product.id AND Product.project = %s' % (
                    sqlvalues(self.project)))

        return '\n AND '.join(constraints)

    def getClauseTables(self):
        """Return the tables that should be added to the FROM clause."""
        if self.project:
            return ['Product']
        else:
            return []

    def getOrderByClause(self):
        """Return the ORDER BY clause to sort the results."""
        sort = self.sort
        if sort is None:
            if self.search_text is not None:
                sort = FAQSort.RELEVANCY
            else:
                sort = FAQSort.NEWEST_FIRST
        if sort is FAQSort.NEWEST_FIRST:
            return "-FAQ.date_created"
        elif sort is FAQSort.OLDEST_FIRST:
            return "FAQ.date_created"
        elif sort is FAQSort.RELEVANCY:
            if self.search_text:
                # SQLConstant is a workaround for bug 53455.
                return [SQLConstant(
                            "-rank(FAQ.fti, ftq(%s))" % quote(
                                self.search_text)),
                        "-FAQ.date_created"]
            else:
                return "-FAQ.date_created"
        else:
            raise AssertionError("Unknown FAQSort value: %r" % sort)


class FAQSet:
    """See `IFAQSet`."""

    implements(IFAQSet)

    def getFAQ(self, id):
        """See `IFAQSet`."""
        return FAQ.getForTarget(id, None)

    def searchFAQs(self, search_text=None, owner=None, sort=None):
        """See `IFAQSet`."""
        return FAQSearch(
            search_text=search_text, owner=owner, sort=sort).getResults()


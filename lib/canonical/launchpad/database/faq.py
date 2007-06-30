# Copyright 2007 Canonical Ltd.  All rights reserved.

"""FAQ document models."""

__metaclass__ = type

__all__ = [
    'FAQ',
    ]

from sqlobject import (
    ForeignKey, SQLMultipleJoin, SQLObjectNotFound, StringCol)
from sqlobject.sqlbuilder import SQLConstant

from zope.interface import implements

from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.nl_search import nl_phrase_search
from canonical.database.sqlbase import quote, SQLBase, sqlvalues

from canonical.launchpad.interfaces import IFAQ, IPerson


class FAQ(SQLBase):
    """See `IFAQ`."""

    implements(IFAQ)

    _table = 'FAQ'
    _defaultOrder = ['date_created', 'id']

    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)

    title = StringCol(notNull=True)

    keywords = StringCol(dbName="tags", notNull=False, default=None)

    content = StringCol(notNull=False, default=None)

    date_created = UtcDateTimeCol(notNull=True, default=DEFAULT)

    last_updated_by = ForeignKey(
        dbName='last_updated_by', foreignKey='Person', notNull=False,
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

        Ensure that only one of url or content, and product or
        distribution is given.
        """
        if not IPerson.providedBy(owner):
            raise AssertionError(
                'owner parameter should be an IPerson: %r' % owner)
        if product is not None and distribution is not None:
             raise AssertionError(
                "only one of product or distribution should be provided")
        if product is None and distribution is None:
            raise AssertionError("product or distribution must be provided")
        if date_created is None:
            date_created = DEFAULT
        return FAQ(
            owner=owner, title=title, content=content, keywords=keywords,
            date_created=date_created, product=product,
            distribution=distribution)

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

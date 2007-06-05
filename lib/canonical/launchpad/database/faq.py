# Copyright 2007 Canonical Ltd.  All rights reserved.

"""FAQ document models."""

__metaclass__ = type

__all__ = [
    'FAQ',
    ]

from sqlobject import ForeignKey, StringCol

from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.interfaces import IFAQ, IPerson


class FAQ(SQLBase):
    """See `IFAQ`."""

    implements(IFAQ)

    _table = 'FAQ'
    _defaultOrder = ['date_created', 'id']

    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)

    title = StringCol(notNull=True)

    summary = StringCol(notNull=True)

    keywords = StringCol(notNull=False, default=None)

    content = StringCol(notNull=False, default=None)

    url = StringCol(notNull=False, default=None)

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

    @property
    def target(self):
        """See `IFAQ`."""
        if self.product:
            return self.product
        else:
            return self.distribution

    @staticmethod
    def new(owner, title, summary, content=None, url=None,
            date_created=None, product=None, distribution=None):
        """Factory method to create a new FAQ.

        It makes sure that only of url or content, and product or
        distribution is given.
        """
        if not IPerson.providedBy(owner):
            raise AssertionError(
                'owner parameter should be an IPerson: %r' % owner)
        if content is not None and url is not None:
            raise AssertionError(
                "only one of url or content should be provided")
        if content is None and url is None:
            raise AssertionError("content or url must be provided")
        if product is not None and distribution is not None:
             raise AssertionError(
                "only one of product or distribution should be provided")
        if product is None and distribution is None:
            raise AssertionError("product or distribution must be provided")
        if date_created is None:
            date_created = DEFAULT
        return FAQ(
            owner=owner, title=title, summary=summary, content=content,
            url=url, date_created=date_created, product=product,
            distribution=distribution)

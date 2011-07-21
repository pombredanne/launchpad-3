# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import lazr.batchnavigator
from lazr.batchnavigator.interfaces import IRangeFactory
from storm import Undef
from storm.expr import Desc
from storm.properties import PropertyColumn
from storm.zope.interfaces import IResultSet
from zope.component import adapts
from zope.interface import implements
from zope.interface.common.sequence import IFiniteSequence
from zope.security.proxy import (
    isinstance as zope_isinstance,
    removeSecurityProxy,
    )

from canonical.config import config
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.webapp.interfaces import (
    ITableBatchNavigator,
    StormRangeFactoryError,
    )
from canonical.launchpad.webapp.publisher import LaunchpadView


class FiniteSequenceAdapter:

    adapts(IResultSet) # and ISQLObjectResultSet
    implements(IFiniteSequence)

    def __init__(self, context):
        self.context = context

    def __getitem__(self, ix):
        return self.context[ix]

    def __iter__(self):
        return iter(self.context)

    def __len__(self):
        return self.context.count()


class BoundReferenceSetAdapter:
    """Adaptor for `BoundReferenceSet` implementations in Storm."""

    implements(IFiniteSequence)

    def __init__(self, context):
        self.context = context

    def __getitem__(self, ix):
        return self.context.find()[ix]

    def __iter__(self):
        return iter(self.context)

    def __len__(self):
        return self.context.count()


class UpperBatchNavigationView(LaunchpadView):
    """Only render navigation links if there is a batch."""

    css_class = "upper-batch-nav"

    def render(self):
        if self.context.currentBatch():
            return LaunchpadView.render(self)
        return u""


class LowerBatchNavigationView(UpperBatchNavigationView):
    """Only render bottom navigation links if there are multiple batches."""

    css_class = "lower-batch-nav"

    def render(self):
        if (self.context.currentBatch() and
            (self.context.nextBatchURL() or
            self.context.prevBatchURL())):
            return LaunchpadView.render(self)
        return u""


class BatchNavigator(lazr.batchnavigator.BatchNavigator):

    @property
    def default_batch_size(self):
        return config.launchpad.default_batch_size

    @property
    def max_batch_size(self):
        return config.launchpad.max_batch_size

    @property
    def has_multiple_pages(self):
        """Whether the total size is greater than the batch size.

        When true, it means that the batch should be rendered on multiple
        pages, and a navigation heading should be included above and below the
        table.
        """
        return self.batch.total() > self.batch.size


class ActiveBatchNavigator(BatchNavigator):
    """A paginator for active items.

    Used when a view needs to display two BatchNavigators.
    """
    variable_name_prefix = 'active'


class InactiveBatchNavigator(BatchNavigator):
    """A paginator for inactive items.

    Used when a view needs to display two Batchavigators.
    """
    variable_name_prefix = 'inactive'


class TableBatchNavigator(BatchNavigator):
    """See canonical.launchpad.interfaces.ITableBatchNavigator."""
    implements(ITableBatchNavigator)

    def __init__(self, results, request, start=0, size=None,
                 columns_to_show=None, callback=None):
        BatchNavigator.__init__(self, results, request, start, size, callback)

        self.show_column = {}
        if columns_to_show:
            for column_to_show in columns_to_show:
                self.show_column[column_to_show] = True


class StormRangeFactory:
    """A range factory for Storm result sets.

    It creates the endpoint memo values from the expressions used in the
    ORDER BY clause.

    Limitations:

    - The order_by expressions must be Storm PropertyColumn instances,
      e.g. Bug.title. Simple strings (e.g., resultset.order_by('Bug.id')
      or general Storm SQL expression are not supported.
    - The objects representing rows of the PropertyColumn's table must
      be contained in the result. I.e.,

          store.find(Bug.id, Bug.id < 10)

      does not work, while

          store.find(Bug, Bug.id < 10)

      works.
    """
    implements(IRangeFactory)

    def __init__(self, resultset):
        """Create a new StormRangeFactory instance.

        :param resultset: A Storm ResultSet instance or a DecoratedResultSet
            instance.
        """
        self.resultset = resultset
        if zope_isinstance(resultset, DecoratedResultSet):
            self.plain_resultset = resultset.getPlainResultSet()
        else:
            self.plain_resultset = resultset

    def getSortExpressions(self):
        """Return the order_by expressions of the result set."""
        return removeSecurityProxy(self.plain_resultset)._order_by

    def getOrderValuesFor(self, row):
        """Return the values of the order_by expressions for the given row.
        """
        sort_values = []
        if not zope_isinstance(row, tuple):
            row = (row, )
        sort_expressions = self.getSortExpressions()
        if sort_expressions is Undef:
            raise StormRangeFactoryError(
                'StormRangeFactory requires a sorted result set.')
        for expression in sort_expressions:
            if zope_isinstance(expression, Desc):
                expression = expression.expr
            if not zope_isinstance(expression, PropertyColumn):
                raise StormRangeFactoryError(
                    'StormRangeFactory supports only sorting by '
                    'PropertyColumn, not by %r.' % expression)
            class_instance_found = False
            for row_part in row:
                if zope_isinstance(row_part, expression.cls):
                    sort_values.append(expression.__get__(row_part))
                    class_instance_found = True
                    break
            if not class_instance_found:
                raise StormRangeFactoryError(
                    'Instances of %r are not contained in the result set, '
                    'but are required to retrieve the value of %s.%s.'
                    % (expression.cls, expression.cls.__name__,
                       expression.name))
        return sort_values

    def getEndpointMemos(self, batch):
        """See `IRangeFactory`."""
        lower = self.getOrderValuesFor(batch.first())
        upper = self.getOrderValuesFor(batch.last())
        # xxx incomplete

    def getSlice(self, size, endpoint_memo='', forwards=True):
        """See `IRangeFactory`."""
        pass #xxxxx incomplete

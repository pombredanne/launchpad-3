# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from datetime import datetime

import lazr.batchnavigator
from lazr.batchnavigator.interfaces import IRangeFactory
import simplejson
from storm import Undef
from storm.expr import Desc
from storm.properties import PropertyColumn
from storm.zope.interfaces import IResultSet
from zope.component import adapts
from zope.interface import implements
from zope.interface.common.sequence import IFiniteSequence
from zope.security.proxy import (
    isinstance as zope_isinstance,
    ProxyFactory,
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

    adapts(IResultSet)
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


class DateTimeJSONEncoder(simplejson.JSONEncoder):
    """A JSON encoder that understands datetime objects.

    Datetime objects are formatted according to ISO 1601.
    """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return simplejson.JSONEncoder.default(self, obj)


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

    def __init__(self, resultset, error_cb=None):
        """Create a new StormRangeFactory instance.

        :param resultset: A Storm ResultSet instance or a DecoratedResultSet
            instance.
        :param error_cb: A function which takes one string as a parameter.
            It is called when the parameter endpoint_memo of getSlice()
            does not match the order settings of a resultset.
        """
        self.resultset = resultset
        if zope_isinstance(resultset, DecoratedResultSet):
            self.plain_resultset = resultset.getPlainResultSet()
        else:
            self.plain_resultset = resultset
        self.error_cb = error_cb

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
        lower = self.getOrderValuesFor(self.plain_resultset[0])
        upper = self.getOrderValuesFor(
            self.plain_resultset[batch.trueSize - 1])
        return (
            simplejson.dumps(lower, cls=DateTimeJSONEncoder),
            simplejson.dumps(upper, cls=DateTimeJSONEncoder),
            )

    def reportError(self, message):
        if self.error_cb is not None:
            self.error_cb(message)

    def parseMemo(self, memo):
        """Convert the given memo string into a sequence of Python objects.

        memo should be a JSON string as returned by getEndpointMemos().

        Note that memo originates from a URL query parameter and can thus
        not be trusted to always contain formally valid and consistent
        data.

        Parsing errors or data not matching the sort parameters of the
        result set are simply ignored.
        """
        if memo == '':
            return None
        try:
            parsed_memo = simplejson.loads(memo)
        except simplejson.JSONDecodeError:
            self.reportError('memo is not a valid JSON string.')
            return None
        if not isinstance(parsed_memo, list):
            self.reportError(
                'memo must be the JSON representation of a list.')
            return None

        sort_expressions = self.getSortExpressions()
        if len(sort_expressions) != len(parsed_memo):
            self.reportError(
                'Invalid number of elements in memo string. '
                'Expected: %i, got: %i'
                % (len(sort_expressions), len(parsed_memo)))
            return None

        converted_memo = []
        for expression, value in zip(sort_expressions, parsed_memo):
            if isinstance(expression, Desc):
                expression = expression.expr
            try:
                expression.variable_factory(value=value)
            except TypeError, error:
                # A TypeError is raised when the type of value cannot
                # be used for expression. All expected types are
                # properly created by simplejson.loads() above, except
                # time stamps which are represented as strings in
                # ISO format. If value is a string and if it can be
                # converted into a datetime object, we have a valid
                # value.
                if (str(error).startswith('Expected datetime') and
                    isinstance(value, str)):
                    try:
                        value = datetime.strptime(
                            value, '%Y-%m-%dT%H:%M:%S.%f')
                    except ValueError:
                        # One more attempt: If the fractions of a second
                        # are zero, datetime.isoformat() omits the
                        # entire part '.000000', so we need a different
                        # format for strptime().
                        try:
                            value = datetime.strptime(
                                value, '%Y-%m-%dT%H:%M:%S')
                        except ValueError:
                            self.reportError(
                                'Invalid datetime value: %r' % value)
                            return None
                else:
                    self.reportError(
                        'Invalid parameter: %r' % value)
                    return None
            converted_memo.append(value)
        return converted_memo

    def reverseSortOrder(self):
        """Return a list of reversed sort expressions."""
        def invert_sort_expression(expr):
            if isinstance(expression, Desc):
                return expression.expr
            else:
                return Desc(expression)

        return [
            invert_sort_expression(expression)
            for expression in self.getSortExpressions()]

    def whereExpressionFromSortExpression(self, expression, memo):
        """Create a Storm expression to be used in the WHERE clause of the
        slice query.
        """
        if isinstance(expression, Desc):
            expression = expression.expr
            return expression < memo
        else:
            return expression > memo

    def getSlice(self, size, endpoint_memo='', forwards=True):
        """See `IRangeFactory`."""
        if not forwards:
            self.resultset.order_by(*self.reverseSortOrder())
        parsed_memo = self.parseMemo(endpoint_memo)
        if parsed_memo is None:
            return self.resultset.config(limit=size)
        else:
            sort_expressions = self.getSortExpressions()
            where = [
                self.whereExpressionFromSortExpression(expression, memo)
                for expression, memo in zip(sort_expressions, parsed_memo)]
            # From storm.zope.interfaces.IResultSet.__doc__:
            #     - C{find()}, C{group_by()} and C{having()} are really
            #       used to configure result sets, so are mostly intended
            #       for use on the model side.
            naked_result = removeSecurityProxy(self.resultset).find(*where)
            result = ProxyFactory(naked_result)
            return result.config(limit=size)

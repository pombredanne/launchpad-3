# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import lazr.batchnavigator
from storm.zope.interfaces import IResultSet
from zope.component import adapts
from zope.interface import implements
from zope.interface.common.sequence import IFiniteSequence

from canonical.config import config
from canonical.launchpad.webapp.interfaces import ITableBatchNavigator
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

    Used when a view needs to display more than one BatchNavigator of items.
    """
    start_variable_name = 'active_start'
    batch_variable_name = 'active_batch'


class InactiveBatchNavigator(BatchNavigator):
    """A paginator for inactive items.

    Used when a view needs to display more than one BatchNavigator of items.
    """
    start_variable_name = 'inactive_start'
    batch_variable_name = 'inactive_batch'


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

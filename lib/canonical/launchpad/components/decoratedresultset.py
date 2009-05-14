# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'DecoratedResultSet',
    ]

from zope.security.proxy import removeSecurityProxy

from storm.expr import Column
from storm.zope.interfaces import IResultSet

from lazr.delegates import delegates


class DecoratedResultSet(object):
    """A decorated Storm ResultSet for 'Magic' (presenter) classes.

    Because `DistroSeriesBinaryPackage` doesn't actually exist in the
    database, the `DistroSeries`.searchPackages method uses the
    `DistroSeriesPackageCache` object to search for packages within a
    `DistroSeries`.

    Nonetheless, the users of the searchPackages method (such as the
    `DistroSeriesView`) expect a result set of DSBPs. Rather than executing
    the query prematurely and doing a list comprehension on the complete
    result set (which could be very large) to convert all the results (even
    though batching may mean only a window of 10 results is required), this
    adapted result set converts the results only when they are needed.

    This behaviour is required for other classes as well (Distribution,
    DistroArchSeries), hence a generalised solution.

    This class also fixes a bug currently in Storm's ResultSet.count
    method (see below)
    """
    delegates(IResultSet, context='result_set')

    def __init__(self, result_set, result_decorator=None, pre_iter_hook=None):
        """
        :param result_set: The original result set to be decorated.
        :param result_decorator: The method with which individual results
            will be passed through before being returned.
        :param pre_iter_hook: The method to be called (with the 'result_set')
            immediately before iteration starts.
        """
        self.result_set = result_set
        self.result_decorator = result_decorator
        self.pre_iter_hook = pre_iter_hook

    def decorate_or_none(self, result):
        """Decorate a result or return None if the result is itself None"""
        if result is None:
            return None
        else:
            if self.result_decorator is None:
                return result
            else:
                return self.result_decorator(result)

    def copy(self, *args, **kwargs):
        """See `IResultSet`.

        :return: The decorated version of the returned result set.
        """
        new_result_set = self.result_set.copy(*args, **kwargs)
        return DecoratedResultSet(
            new_result_set, self.result_decorator, self.pre_iter_hook)

    def config(self, *args, **kwargs):
        """See `IResultSet`.

        :return: The decorated result set.after updating the config.
        """
        self.result_set.config(*args, **kwargs)
        return self

    def __iter__(self, *args, **kwargs):
        """See `IResultSet`.

        Yield a decorated version of the returned value.
        """
        # Execute/evaluate the result set query.
        results = list(self.result_set.__iter__(*args, **kwargs))
        if self.pre_iter_hook is not None:
            self.pre_iter_hook(results)
        for value in results:
            yield self.decorate_or_none(value)

    def __getitem__(self, *args, **kwargs):
        """See `IResultSet`.

        :return: The decorated version of the returned value.
        """
        # Can be a value or result set...
        value = self.result_set.__getitem__(*args, **kwargs)
        if isinstance(value, type(self.result_set)):
            return DecoratedResultSet(
                value, self.result_decorator, self.pre_iter_hook)
        else:
            return self.decorate_or_none(value)

    def any(self, *args, **kwargs):
        """See `IResultSet`.

        :return: The decorated version of the returned value.
        """
        value = self.result_set.any(*args, **kwargs)
        return self.decorate_or_none(value)

    def first(self, *args, **kwargs):
        """See `IResultSet`.

        :return: The decorated version of the returned value.
        """
        value = self.result_set.first(*args, **kwargs)
        return self.decorate_or_none(value)

    def last(self, *args, **kwargs):
        """See `IResultSet`.

        :return: The decorated version of the returned value.
        """
        value = self.result_set.last(*args, **kwargs)
        return self.decorate_or_none(value)

    def one(self, *args, **kwargs):
        """See `IResultSet`.

        :return: The decorated version of the returned value.
        """
        value = self.result_set.one(*args, **kwargs)
        return self.decorate_or_none(value)

    def order_by(self, *args, **kwargs):
        """See `IResultSet`.

        :return: The decorated version of the returned result set.
        """
        new_result_set = self.result_set.order_by(*args, **kwargs)
        return DecoratedResultSet(
            new_result_set, self.result_decorator, self.pre_iter_hook)

    def count(self, *args, **kwargs):
        """See `IResultSet`.

        Decorated to fix bug 217644

        Currently Storm.store.ResultSet has a bug where aggregate
        methods do not respect the distinct config option. This
        decorated version ensures that the count method *does* respect
        the distinct config option when called without args/kwargs.
        """
        # Only override the method call if
        #  1) The result set has the distinct config set
        #  2) count was called without any args or kwargs
        is_distinct = removeSecurityProxy(self.result_set)._distinct
        if is_distinct and len(args) == 0 and len(kwargs) == 0:
            spec = self.result_set._find_spec
            columns, tables = spec.get_columns_and_tables()

            # Note: The following looks a bit suspect because it will only
            # work if the original result set includes an id column. But this
            # should always be the case when using a DecoratedResultSet as
            # we're decorating content classes.
            main_id_column = Column('id', tables[0])
            return self.result_set.count(expr=main_id_column, distinct=True)
        else:
            return self.result_set.count(*args, **kwargs)

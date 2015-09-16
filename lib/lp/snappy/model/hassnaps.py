# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Mixin classes for objects that implement IHasSnaps."""

__metaclass__ = type
__all__ = [
    'HasSnapsMixin',
    ]

from functools import partial

from zope.component import getUtility

from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.webapp.interfaces import ILaunchBag
from lp.snappy.interfaces.snap import ISnapSet


class HasSnapsMixin:
    """A mixin implementation for `IHasSnaps`."""

    def getSnaps(self, eager_load=False, order_by_date=True):
        user = getUtility(ILaunchBag).user
        snaps = getUtility(ISnapSet).findByContext(
            self, visible_by_user=user, order_by_date=order_by_date)
        if not eager_load:
            return snaps
        else:
            loader = partial(
                getUtility(ISnapSet).preloadDataForSnaps, user=user)
            return DecoratedResultSet(snaps, pre_iter_hook=loader)

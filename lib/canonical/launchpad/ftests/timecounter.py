# Copyright 2007 Canonical Ltd.  All rights reserved.

"""The time_counter is a handy function to use in doctests."""

__metaclass__ = type
__all__ = []

from datetime import datetime, timedelta
from pytz import UTC


def time_counter(origin=None, delta=timedelta(seconds=5)):
    """A generator for yielding datetime values.

    Each time the generator yields a value, the origin is incremented
    by the delta.

    >>> now = time_counter(datetime(2007, 12, 1), timedelta(days=1))
    >>> now.next()
    datetime.datetime(2007, 12, 1, 0, 0)
    >>> now.next()
    datetime.datetime(2007, 12, 2, 0, 0)
    >>> now.next()
    datetime.datetime(2007, 12, 3, 0, 0)
    """
    if origin is None:
        origin = datetime.now(UTC)
    now = origin
    while True:
        yield now
        now += delta

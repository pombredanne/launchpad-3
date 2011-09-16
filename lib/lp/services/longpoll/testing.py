# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Things that help with testing of longpoll."""

__metaclass__ = type
__all__ = [
    "capture_longpoll_emissions",
    ]

from collections import namedtuple
from contextlib import contextmanager
from functools import partial

from lp.app.longpoll.adapters import event


LongPollEventRecord = namedtuple(
    "LongPollEventRecord", ("event_key", "data"))


class LoggingRouter:
    """A test double for instances of `RabbitRoutingKey`.

    Saves messages as `LongPollEventRecord` tuples to a log.
    """

    def __init__(self, event_key, log):
        self.event_key = event_key
        self.log = log

    def send(self, data):
        record = LongPollEventRecord(self.event_key, data)
        self.log.append(record)


@contextmanager
def capture_longpoll_emissions():
    """Capture longpoll emissions while this context is in force.

    This returns a list in which `LongPollEventRecord` tuples will be
    recorded, in the order they're emitted.
    """
    log = []
    original_router_factory = event.router_factory
    event.router_factory = partial(LoggingRouter, log=log)
    try:
        yield log
    finally:
        event.router_factory = original_router_factory

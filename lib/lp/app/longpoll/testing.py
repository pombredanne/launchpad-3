# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Things that help with testing of longpoll."""

__metaclass__ = type
__all__ = [
    "capture_longpoll_emissions",
    ]

from contextlib import contextmanager

from lp.app.longpoll.adapters import event


class LoggingRouterFactory:
    """A drop-in test double for `RabbitRoutingKey`.

    While `RabbitRoutingKey` returns instances of itself, this returns
    instances of `LoggingRouter`.
    """

    def __init__(self):
        self.log = []

    def __call__(self, event_key):
        return LoggingRouter(self, event_key)


class LoggingRouter:
    """A test double for instances of `RabbitRoutingKey`.

    Saves sent messages to a log.
    """

    def __init__(self, factory, event_key):
        self.factory = factory
        self.event_key = event_key

    def send(self, data):
        self.factory.log.append((self.event_key, data))


@contextmanager
def capture_longpoll_emissions():
    """Capture longpoll emissions while this context is in force.

    This returns a list in which 2-tuples of `(event_key, payload)` will be
    recorded, in the order they're emitted.
    """
    original_router_factory = event.router_factory
    event.router_factory = LoggingRouterFactory()
    try:
        yield event.router_factory.log
    finally:
        event.router_factory = original_router_factory

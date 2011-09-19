# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long-poll infrastructure."""

__metaclass__ = type
__all__ = [
    "emit",
    "subscribe",
    ]

from lazr.restful.utils import get_current_browser_request
from zope.component import getMultiAdapter

from lp.services.longpoll.interfaces import (
    ILongPollEvent,
    ILongPollSubscriber,
    )


def subscribe(target, event, request=None):
    """Convenience method to subscribe the current request.

    :param target: Something that can be adapted to `ILongPollEvent`.
    :param event: The name of the event to subscribe to.
    :param request: The request for which to get an `ILongPollSubscriber`. It
        a request is not specified the currently active request is used.
    :return: The `ILongPollEvent` that has been subscribed to.
    """
    event = getMultiAdapter((target, event), ILongPollEvent)
    if request is None:
        request = get_current_browser_request()
    subscriber = ILongPollSubscriber(request)
    subscriber.subscribe(event)
    return event


def emit(source, event, data):
    """Convenience method to emit a message for an event.

    :param source: Something, along with `event`, that can be adapted to
        `ILongPollEvent`.
    :param event: A name/key of the event that is emitted.
    :return: The `ILongPollEvent` that has been emitted.
    """
    event = getMultiAdapter((source, event), ILongPollEvent)
    event.emit(data)
    return event

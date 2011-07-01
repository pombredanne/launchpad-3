# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long-poll infrastructure."""

__metaclass__ = type
__all__ = [
    "emit",
    "subscribe",
    ]

from .interfaces import (
    ILongPollEmitter,
    ILongPollSubscriber,
    )
from lazr.restful.utils import get_current_browser_request
from zope.component import getMultiAdapter

from lp.services.messaging.utility import messaging


def subscribe(target, event):
    """Convenience method to subscribe the current request.

    :param target: Something that can be adapted to `ILongPollEmitter`.
    :param event: The name of the event to subscribe to.

    :return: The key that has been subscribed to.
    """
    emitter = getMultiAdapter((target, event), ILongPollEmitter)
    request = get_current_browser_request()
    ILongPollSubscriber(request).subscribe(emitter)
    return emitter.emit_key


def emit(source, event, data):
    """Convenience method to emit a message for an event.

    :param source: Something that can be adapted to `ILongPollEmitter`.
    :param event: The name/key of the event to subscribe to.

    :return: The key that has been subscribed to.
    """
    emitter = getMultiAdapter((source, event), ILongPollEmitter)
    messaging.send(emitter.emit_key, data)

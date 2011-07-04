# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long-poll infrastructure interfaces."""

__metaclass__ = type
__all__ = [
    "ILongPollEmitter",
    "ILongPollSubscriber",
    ]


from zope.interface import (
    Attribute,
    Interface,
    )


class ILongPollEmitter(Interface):

    source = Attribute(
        "The event source.")

    event = Attribute(
        "An object indicating the type of event.")

    emit_key = Attribute(
        "The key with which events will be emitted. Should be predictable "
        "and stable.")

    def emit(data):
        """Emit the given data to `emit_key`.

        :param data: Any data structure that can be dumped as JSON.
        """


class ILongPollSubscriber(Interface):

    subscribe_key = Attribute(
        "The key which the subscriber must know in order to be able "
        "to long-poll for subscribed events. Should be infeasible to "
        "guess, a UUID for example.")

    def subscribe(emitter):
        """Subscribe to the given event emitter.

        :type emitter: ILongPollEmitter
        """

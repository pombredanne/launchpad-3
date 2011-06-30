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

    emit_key = Attribute(
        "The key with which events will be emitted. Should be predictable "
        "and stable.")


class ILongPollSubscriber(Interface):

    # XXX: Probably don't need this.
    subscribe_key = Attribute(
        "The key which the subscriber must know in order to be able "
        "to long-poll for subscribed events. Should be infeasible to "
        "guess, a UUID for example.")

    def subscribe(emitter):
        """Subscribe to the given event emitter.

        :type emitter: ILongPollEmitter
        """

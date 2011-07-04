# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long-poll subscriber adapter tests."""

__metaclass__ = type

from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.app.longpoll.adapters.emitter import LongPollEmitter
from lp.app.longpoll.interfaces import ILongPollEmitter
from lp.services.messaging.queue import RabbitMessageBase
from lp.testing import TestCase
from lp.testing.matchers import Contains


class FakeEmitter(LongPollEmitter):

    @property
    def emit_key(self):
        return "emit-key-%s-%s" % (self.source, self.event)


class TestLongPollEmitter(TestCase):

    layer = LaunchpadFunctionalLayer

    def test_interface(self):
        emitter = FakeEmitter("source", "event")
        self.assertProvides(emitter, ILongPollEmitter)

    def test_emit_key(self):
        # emit_key is not implemented in LongPollEmitter; subclasses must
        # provide it.
        emitter = LongPollEmitter("source", "event")
        self.assertRaises(NotImplementedError, getattr, emitter, "emit_key")

    def test_emit(self):
        # LongPollEmitter.emit() sends the given data to `emit_key`.
        emitter = FakeEmitter("source", "event")
        emitter.emit({"hello": 1234})
        messages = [
            message for (call, message) in
            RabbitMessageBase.class_locals.messages]
        self.assertThat(
            messages, Contains(message))

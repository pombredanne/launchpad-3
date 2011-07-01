# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Long-poll subscriber adapter tests."""

__metaclass__ = type

from itertools import count

from lp.app.longpoll import subscribe, emit
from lp.app.longpoll.interfaces import ILongPollEmitter
from zope.interface import implements

from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.testing import TestCase


class FakeEmitter:

    implements(ILongPollEmitter)

    emit_key_indexes = count(1)

    def __init__(self):
        self.emit_key = "emit-key-%d" % next(self.emit_key_indexes)


class TestSubscribe(TestCase):

    layer = LaunchpadFunctionalLayer

    def test_subscribe(self):
        # TODO
        subscribe


class TestEmit(TestCase):

    layer = LaunchpadFunctionalLayer

    def test_emit(self):
        # TODO
        emit

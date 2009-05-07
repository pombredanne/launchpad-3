# Copyright 2009 Canonical Ltd.  All rights reserved.

"""XXX."""

__metaclass__ = type

import unittest

import bzrlib.ui

from canonical.codehosting.codeimport.uifactory import LoggingUIFactory
from canonical.launchpad.testing import FakeTime, TestCase


def _set_ui_factory(factory):
    bzrlib.ui.ui_factory = factory


class StubFile(object):

    def __init__(self):
        self.msgs = []

    def write(self, msg):
        self.msgs.append(msg)

    def messages_without_timestamps(self):
        cleaned_msgs = []
        for m in self.msgs:
            cleaned_msgs.append(m[m.find(']')+1:].strip())
        return cleaned_msgs


class TestLoggingUIFactory(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.addCleanup(_set_ui_factory, bzrlib.ui.ui_factory)
        self.fake_time = FakeTime(12345)
        self.stub_file = StubFile()

    def makeLoggingUIFactory(self):
        return LoggingUIFactory(
            time_source=self.fake_time.now, output=self.stub_file)

    def test_first_progress_updates(self):
        # The first call to progress generates some output.
        factory = self.makeLoggingUIFactory()
        bar = factory.nested_progress_bar()
        bar.update("hi")
        self.assertEqual(
            ['hi'], self.stub_file.messages_without_timestamps())

    def test_second_rapid_progress_doesnt_update(self):
        # The second of two progress calls that are less than the factory's
        # interval apart does not generate output.
        factory = self.makeLoggingUIFactory()
        bar = factory.nested_progress_bar()
        bar.update("hi")
        self.fake_time.advance(factory.interval / 2)
        bar.update("there")
        self.assertEqual(
            ['hi'], self.stub_file.messages_without_timestamps())

    def test_second_slow_progress_updates(self):
        # The second of two progress calls that are more than the factory's
        # interval apart does generate output.
        factory = self.makeLoggingUIFactory()
        bar = factory.nested_progress_bar()
        bar.update("hi")
        self.fake_time.advance(factory.interval * 2)
        bar.update("there")
        self.assertEqual(
            ['hi', 'there'], self.stub_file.messages_without_timestamps())


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


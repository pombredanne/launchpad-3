# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0102

"""Tests for `LoggingUIFactory`."""

__metaclass__ = type

import unittest

from lp.codehosting.codeimport.uifactory import LoggingUIFactory
from lp.testing import (
    FakeTime,
    TestCase,
    )


class TestLoggingUIFactory(TestCase):
    """Tests for `LoggingUIFactory`."""

    def setUp(self):
        TestCase.setUp(self)
        self.fake_time = FakeTime(12345)
        self.messages = []

    def makeLoggingUIFactory(self):
        """Make a `LoggingUIFactory` with fake time and contained output."""
        return LoggingUIFactory(
            time_source=self.fake_time.now, writer=self.messages.append)

    def test_first_progress_updates(self):
        # The first call to progress generates some output.
        factory = self.makeLoggingUIFactory()
        bar = factory.nested_progress_bar()
        bar.update("hi")
        self.assertEqual(['hi'], self.messages)

    def test_second_rapid_progress_doesnt_update(self):
        # The second of two progress calls that are less than the factory's
        # interval apart does not generate output.
        factory = self.makeLoggingUIFactory()
        bar = factory.nested_progress_bar()
        bar.update("hi")
        self.fake_time.advance(factory.interval / 2)
        bar.update("there")
        self.assertEqual(['hi'], self.messages)

    def test_second_slow_progress_updates(self):
        # The second of two progress calls that are more than the factory's
        # interval apart does generate output.
        factory = self.makeLoggingUIFactory()
        bar = factory.nested_progress_bar()
        bar.update("hi")
        self.fake_time.advance(factory.interval * 2)
        bar.update("there")
        self.assertEqual(['hi', 'there'], self.messages)

    def test_first_progress_on_new_bar_updates(self):
        # The first progress on a new progress task always generates output.
        factory = self.makeLoggingUIFactory()
        bar = factory.nested_progress_bar()
        bar.update("hi")
        self.fake_time.advance(factory.interval / 2)
        bar2 = factory.nested_progress_bar()
        bar2.update("there")
        self.assertEqual(['hi', 'hi:there'], self.messages)

    def test_update_with_count_formats_nicely(self):
        # When more details are passed to update, they are formatted nicely.
        factory = self.makeLoggingUIFactory()
        bar = factory.nested_progress_bar()
        bar.update("hi", 1, 8)
        self.assertEqual(['hi 1/8'], self.messages)

    def test_report_transport_activity_reports_bytes_since_last_update(self):
        # If there is no call to _progress_updated for 'interval' seconds, the
        # next call to report_transport_activity will report however many
        # bytes have been transferred since the update.
        factory = self.makeLoggingUIFactory()
        bar = factory.nested_progress_bar()
        bar.update("hi", 1, 10)
        self.fake_time.advance(factory.interval / 2)
        # The bytes in this call will not be reported:
        factory.report_transport_activity(None, 1, 'read')
        self.fake_time.advance(factory.interval)
        bar.update("hi", 2, 10)
        self.fake_time.advance(factory.interval / 2)
        factory.report_transport_activity(None, 10, 'read')
        self.fake_time.advance(factory.interval)
        factory.report_transport_activity(None, 100, 'read')
        self.fake_time.advance(factory.interval * 2)
        # This call will cause output that does not include the transport
        # activity info.
        bar.update("hi", 3, 10)
        self.assertEqual(
            ['hi 1/10', 'hi 2/10', '110 bytes transferred | hi 2/10',
             'hi 3/10'],
            self.messages)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


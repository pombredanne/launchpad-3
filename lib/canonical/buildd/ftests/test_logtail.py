# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
"""Buildd logtail mechanisms tests."""

__metaclass__ = type

__all__ = ['BuilddLogtailTests']


import unittest
from canonical.buildd.ftests.harness import BuilddTestCase


class BuilddLogtailTests(BuilddTestCase):
    """Unit tests for logtail mechanisms."""

    def testLogtail(self):
        """Tests the logtail mechanisms.

        'getLogTail' return up to 2 KiB text from the current 'buildlog' file.
        """
        self.makeLog(0)
        log_tail = self.slave.getLogTail()
        self.assertEqual(len(log_tail), 0)

        self.makeLog(1)
        log_tail = self.slave.getLogTail()
        self.assertEqual(len(log_tail), 1)

        self.makeLog(2048)
        log_tail = self.slave.getLogTail()
        self.assertEqual(len(log_tail), 2048)

        self.makeLog(2049)
        log_tail = self.slave.getLogTail()
        self.assertEqual(len(log_tail), 2048)

        self.makeLog(4096)
        log_tail = self.slave.getLogTail()
        self.assertEqual(len(log_tail), 2048)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

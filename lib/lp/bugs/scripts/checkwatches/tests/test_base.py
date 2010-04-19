# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the `base` module."""

from __future__ import with_statement

__metaclass__ = type

import unittest

from contextlib import contextmanager

import transaction

from canonical.launchpad.webapp.adapter import get_request_statements
from canonical.launchpad.scripts.logger import QuietFakeLogger
from canonical.testing import LaunchpadZopelessLayer

from lp.testing import TestCaseWithFactory

from ..base import WorkingBase


class TestWorkingBase(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_statement_logging(self):
        person = self.factory.makePerson()
        email = person.preferredemail.email
        logger = QuietFakeLogger()
        base = WorkingBase(email, transaction.manager, logger)
        self.factory.makeEmail('numpty1@example.com', person)
        self.assertEqual(
            0, len(get_request_statements()),
            "The statement log should be empty because "
            "logging is not enabled.")
        with base.statement_logging:
            self.assertEqual(
                0, len(get_request_statements()),
                "There should be no statements in the log yet.")
            self.factory.makeEmail('numpty2@example.com', person)
            self.assertTrue(
                len(get_request_statements()) > 0,
                "There should be at least one statement in the log.")
        self.assertEqual(
            0, len(get_request_statements()),
            "SQL statement log not cleared on exit "
            "from base.statement_logging.")


class TestWorkingBaseErrorReporting(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    @contextmanager
    def _test_sql_log_cleared_after_x(self):
        person = self.factory.makePerson()
        email = person.preferredemail.email
        logger = QuietFakeLogger()
        base = WorkingBase(email, transaction.manager, logger)
        with base.statement_logging:
            self.factory.makeEmail('numpty@example.com', person)
            self.assertTrue(
                len(get_request_statements()) > 0,
                "We need at least one statement in the SQL log.")
            yield base
            self.assertTrue(
                len(get_request_statements()) == 0,
                "SQL statement log not cleared by WorkingBase.warning().")

    def test_sql_log_cleared_after_warning(self):
        with self._test_sql_log_cleared_after_x() as base:
            base.warning("Numpty on deck.")

    def test_sql_log_cleared_after_error(self):
        with self._test_sql_log_cleared_after_x() as base:
            base.error("Numpty on deck.")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

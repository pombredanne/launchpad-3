# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Tests for bugtask.py."""

__metaclass__ = type

from zope.testing.doctest import DocTestSuite
from zope.testing.doctest import REPORT_NDIFF, NORMALIZE_WHITESPACE, ELLIPSIS


def test_open_and_resolved_statuses(self):
    """
    There are constants that are used to define which statuses are for
    resolved bugs (RESOLVED_BUGTASK_STATUSES), and which are for
    unresolved bugs (UNRESOLVED_BUGTASK_STATUSES). The two constants
    include all statuses defined in BugTaskStatus, except for Unknown.

        >>> from canonical.launchpad.interfaces import (
        ...     RESOLVED_BUGTASK_STATUSES, UNRESOLVED_BUGTASK_STATUSES)
        >>> from canonical.launchpad.interfaces import BugTaskStatus
        >>> not_included_status = set(BugTaskStatus.items).difference(
        ...     RESOLVED_BUGTASK_STATUSES + UNRESOLVED_BUGTASK_STATUSES)
        >>> [status.name for status in not_included_status]
        ['UNKNOWN']
    """

def test_suite():
    suite = DocTestSuite(
        optionflags=REPORT_NDIFF|NORMALIZE_WHITESPACE|ELLIPSIS)
    return suite


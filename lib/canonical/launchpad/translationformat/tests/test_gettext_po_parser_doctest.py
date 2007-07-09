# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test harness for running the gettext_po_parser.txt test.

Tests with different sample .po files so we are sure the parsed data is
correct.
"""

__metaclass__ = type

__all__ = []

from zope.testing.doctest import DocFileSuite
from canonical.launchpad.ftests.test_system_documentation import (
    default_optionflags)


def test_suite():
    return DocFileSuite(
        'gettext_po_parser.txt', optionflags=default_optionflags)

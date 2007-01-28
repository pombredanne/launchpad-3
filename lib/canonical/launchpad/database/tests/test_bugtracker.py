# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.testing.doctest import NORMALIZE_WHITESPACE, ELLIPSIS
from zope.testing.doctestunit import DocTestSuite


def test_suite():
    return DocTestSuite(
        'canonical.launchpad.database.bugtracker',
        optionflags=NORMALIZE_WHITESPACE|ELLIPSIS)


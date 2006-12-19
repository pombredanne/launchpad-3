# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Test for virtual host setup."""

__metaclass__ = type

from zope.testing.doctest import DocTestSuite, NORMALIZE_WHITESPACE, ELLIPSIS

def test_suite():
    suite = DocTestSuite(
            'canonical.launchpad.webapp.vhosts',
            optionflags=NORMALIZE_WHITESPACE | ELLIPSIS
            )
    return suite


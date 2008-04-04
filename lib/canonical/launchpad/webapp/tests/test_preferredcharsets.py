# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Tests for choosing the preferred charsets."""

__metaclass__ = type

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite


def test_suite():
    return LayeredDocFileSuite(
        'test_preferredcharsets.txt')


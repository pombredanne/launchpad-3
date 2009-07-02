# Copyright 2008 Canonical Ltd.  All rights reserved.
"""Tests for person.py."""

__all__ = [
    'test_suite',
    ]

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite


def test_suite():
    return LayeredDocFileSuite('person_from_principal.txt')


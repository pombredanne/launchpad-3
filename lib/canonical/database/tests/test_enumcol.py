# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Run the doctests defined in the enumcol module."""

__metaclass__ = type
__all__ = []


from zope.testing import doctest
import canonical.database.enumcol


def test_suite():
    return doctest.DocTestSuite(canonical.database.enumcol)

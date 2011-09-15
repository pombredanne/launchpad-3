# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Tests to make sure that initZopeless works as expected.
"""

from doctest import DocTestSuite
from canonical.lp import initZopeless
from canonical.testing.layers import ZopelessDatabaseLayer


def test_isZopeless():
    """
    >>> from canonical.lp import isZopeless

    >>> isZopeless()
    False

    >>> tm = initZopeless(dbuser='launchpad')
    >>> isZopeless()
    True

    >>> tm.uninstall()
    >>> isZopeless()
    False

    """


def test_suite():
    doctests = DocTestSuite()
    doctests.layer = ZopelessDatabaseLayer
    return doctests

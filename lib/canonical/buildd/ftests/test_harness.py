# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.testing import doctest

def test_suite():
    return doctest.DocTestSuite('canonical.buildd.ftests.harness')


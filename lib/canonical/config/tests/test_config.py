# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.testing.doctest import DocTestSuite

def test_suite():
    suite = DocTestSuite('canonical.config')
    return suite



# Copyright 2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.testing.doctestunit import DocTestSuite

def test_suite():
    return DocTestSuite('canonical.launchpad.scripts.rosetta')


# Copyright 2004 Canonical Ltd.  All rights reserved.

from zope.testing.doctestunit import DocFileSuite

def test_suite():
    suite = DocFileSuite('chunkydiff.txt')
    return suite


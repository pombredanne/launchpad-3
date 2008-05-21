# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

from zope.testing import doctest

def test_suite():
    return doctest.DocTestSuite(
            'canonical.launchpad.testing.tests.googleserviceharness',
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
            )

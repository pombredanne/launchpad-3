# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

from zope.testing.doctest import DocTestSuite, NORMALIZE_WHITESPACE, ELLIPSIS

def test_suite():
    suite = DocTestSuite(
            'canonical.launchpad.mailman.config',
            optionflags=NORMALIZE_WHITESPACE | ELLIPSIS
            )
    return suite



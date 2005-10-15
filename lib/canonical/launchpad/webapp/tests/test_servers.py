# Copyright Canonical Limited, 2005, all rights reserved.

__metaclass__ = type

from zope.testing.doctest import DocTestSuite, NORMALIZE_WHITESPACE, ELLIPSIS

def test_suite():
    suite = DocTestSuite(
            'canonical.launchpad.webapp.servers',
            optionflags=NORMALIZE_WHITESPACE | ELLIPSIS
            )
    return suite


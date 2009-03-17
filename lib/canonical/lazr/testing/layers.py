# Copyright 2008-2009 Canonical Ltd.  All rights reserved.

"""Miscellaneous testing helpers."""

__metaclass__ = type
__all__ = [
    'MockRootFolder',
]

class MockRootFolder:
    """Implement the minimum functionality required by Z3 ZODB dependencies

    Installed as part of FunctionalLayer.testSetUp() to allow the http()
    method (zope.app.testing.functional.HTTPCaller) to work.
    """
    @property
    def _p_jar(self):
        return self
    def sync(self):
        pass

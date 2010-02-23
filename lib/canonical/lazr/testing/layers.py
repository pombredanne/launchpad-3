# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
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

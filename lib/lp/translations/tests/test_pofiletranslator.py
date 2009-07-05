# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Runs the POFileTranslator test."""

__metaclass__ = type

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.testing import DatabaseLayer


def test_suite():
    return LayeredDocFileSuite(
        'pofiletranslator.txt', layer=DatabaseLayer)

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Runs the POFileTranslator test."""

__metaclass__ = type

from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite
from canonical.testing.layers import DatabaseLayer


def test_suite():
    return LayeredDocFileSuite(
        'pofiletranslator.txt', layer=DatabaseLayer)

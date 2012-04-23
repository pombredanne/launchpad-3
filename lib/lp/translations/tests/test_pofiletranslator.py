# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Runs the POFileTranslator test."""

__metaclass__ = type

from lp.testing.layers import DatabaseLayer
from lp.testing.systemdocs import LayeredDocFileSuite


def test_suite():
    return LayeredDocFileSuite(
        'pofiletranslator.txt', layer=DatabaseLayer)

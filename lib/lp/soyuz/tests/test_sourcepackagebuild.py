# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type

import unittest

import transaction
from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer

from lp.soyuz.interfaces.sourcepackagebuild import (
    ISourcePackageBuild, ISourcePackageBuildSource)
from lp.testing import TestCaseWithFactory


class TestSourcePackageBuild(TestCaseWithFactory):
    """Test the source package build object."""

    layer = DatabaseFunctionalLayer

    def makeSourcePackageBuild(self):
        return getUtility(ISourcePackageBuildSource).new()

    def test_providesInterface(self):
        # SourcePackageBuild provides ISourcePackageBuild.
        spb = self.makeSourcePackageBuild()
        self.assertProvides(spb, ISourcePackageBuild)

    def test_saves_record(self):
        spb = self.makeSourcePackageBuild()
        transaction.commit()
        self.assertProvides(spb, ISourcePackageBuild)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

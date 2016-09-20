# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for classes that implement IHasGitRepositories."""

__metaclass__ = type

from lp.code.interfaces.hasgitrepositories import IHasGitRepositories
from lp.testing import (
    TestCaseWithFactory,
    verifyObject,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestIHasGitRepositories(TestCaseWithFactory):
    """Test that the correct objects implement the interface."""

    layer = DatabaseFunctionalLayer

    def test_project_implements_hasgitrepositories(self):
        # Projects should implement IHasGitRepositories.
        project = self.factory.makeProduct()
        verifyObject(IHasGitRepositories, project)

    def test_dsp_implements_hasgitrepositories(self):
        # DistributionSourcePackages should implement IHasGitRepositories.
        dsp = self.factory.makeDistributionSourcePackage()
        verifyObject(IHasGitRepositories, dsp)

    def test_person_implements_hasgitrepositories(self):
        # People should implement IHasGitRepositories.
        person = self.factory.makePerson()
        verifyObject(IHasGitRepositories, person)

# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for classes that implement IHasSnaps."""

__metaclass__ = type

from lp.services.features.testing import FeatureFixture
from lp.snappy.interfaces.hassnaps import IHasSnaps
from lp.snappy.interfaces.snap import SNAP_FEATURE_FLAG
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestIHasSnaps(TestCaseWithFactory):
    """Test that the correct objects implement the interface."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestIHasSnaps, self).setUp()
        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: u"on"}))

    def test_branch_implements_hasrecipes(self):
        # Branches should implement IHasSnaps.
        branch = self.factory.makeBranch()
        self.assertProvides(branch, IHasSnaps)

    def test_branch_recipes(self):
        # IBranch.snaps should provide all the Snaps attached to that
        # branch.
        branch = self.factory.makeBranch()
        self.factory.makeSnap(branch=branch)
        self.factory.makeSnap(branch=branch)
        self.factory.makeSnap()
        self.assertEqual(2, branch.snaps.count())

    def test_git_repository_implements_hasrecipes(self):
        # Git repositories should implement IHasSnaps.
        repository = self.factory.makeGitRepository()
        self.assertProvides(repository, IHasSnaps)

    def test_git_repository_recipes(self):
        # IGitRepository.snaps should provide all the Snaps attached to that
        # repository.
        repository = self.factory.makeGitRepository()
        [ref1, ref2] = self.factory.makeGitRefs(
            repository=repository, paths=[u"refs/heads/1", u"refs/heads/2"])
        self.factory.makeSnap(git_ref=ref1)
        self.factory.makeSnap(git_ref=ref2)
        self.factory.makeSnap()
        self.assertEqual(2, repository.snaps.count())

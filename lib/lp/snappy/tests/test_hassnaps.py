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

    def test_branch_implements_hassnaps(self):
        branch = self.factory.makeBranch()
        self.assertProvides(branch, IHasSnaps)

    def test_branch_getSnaps(self):
        # IBranch.getSnaps returns all the Snaps based on that branch.
        branch = self.factory.makeBranch()
        self.factory.makeSnap(branch=branch)
        self.factory.makeSnap(branch=branch)
        self.factory.makeSnap()
        self.assertEqual(2, branch.getSnaps().count())

    def test_git_repository_implements_hassnaps(self):
        repository = self.factory.makeGitRepository()
        self.assertProvides(repository, IHasSnaps)

    def test_git_repository_getSnaps(self):
        # IGitRepository.getSnaps returns all the Snaps based on that
        # repository.
        repository = self.factory.makeGitRepository()
        [ref] = self.factory.makeGitRefs(repository=repository)
        self.factory.makeSnap(git_ref=ref)
        self.factory.makeSnap(git_ref=ref)
        self.factory.makeSnap()
        self.assertEqual(2, repository.getSnaps().count())

    def test_git_ref_implements_hassnaps(self):
        [ref] = self.factory.makeGitRefs()
        self.assertProvides(ref, IHasSnaps)

    def test_git_ref_getSnaps(self):
        # IGitRef.getSnaps returns all the Snaps based on that ref.
        [ref] = self.factory.makeGitRefs()
        self.factory.makeSnap(git_ref=ref)
        self.factory.makeSnap(git_ref=ref)
        self.factory.makeSnap()
        self.assertEqual(2, ref.getSnaps().count())

    def test_person_implements_hassnaps(self):
        person = self.factory.makePerson()
        self.assertProvides(person, IHasSnaps)

    def test_person_getSnaps(self):
        # IPerson.getSnaps returns all the Snaps owned by that person or
        # based on branches or repositories owned by that person.
        person = self.factory.makePerson()
        self.factory.makeSnap(registrant=person, owner=person)
        self.factory.makeSnap(branch=self.factory.makeAnyBranch(owner=person))
        [ref] = self.factory.makeGitRefs(owner=person)
        self.factory.makeSnap(git_ref=ref)
        self.factory.makeSnap()
        self.assertEqual(3, person.getSnaps().count())

    def test_project_implements_hassnaps(self):
        project = self.factory.makeProduct()
        self.assertProvides(project, IHasSnaps)

    def test_project_getSnaps(self):
        # IProduct.getSnaps returns all the Snaps based on that project's
        # branches or repositories.
        project = self.factory.makeProduct()
        self.factory.makeSnap(
            branch=self.factory.makeProductBranch(product=project))
        [ref] = self.factory.makeGitRefs(target=project)
        self.factory.makeSnap(git_ref=ref)
        self.factory.makeSnap()
        self.assertEqual(2, project.getSnaps().count())

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the SourcePackageRecipe content type."""

__metaclass__ = type

import textwrap
import unittest

from bzrlib.plugins.builder.recipe import RecipeParser

from storm.locals import Store

from zope.component import getUtility
from zope.security.interfaces import Unauthorized

from canonical.testing.layers import DatabaseFunctionalLayer

from lp.services.job.interfaces.job import (
    IJob, JobStatus)
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.buildqueue import (
    IBuildQueue)
from lp.soyuz.interfaces.sourcepackagerecipe import (
    ForbiddenInstruction, ISourcePackageRecipe, ISourcePackageRecipeSource,
    TooNewRecipeFormat)
from lp.soyuz.interfaces.sourcepackagerecipebuild import (
    ISourcePackageRecipeBuild, ISourcePackageRecipeBuildJob)
from lp.soyuz.model.buildqueue import (
    BuildQueue)
from lp.soyuz.model.sourcepackagerecipebuild import (
    SourcePackageRecipeBuildJob)
from lp.testing import login_person, TestCaseWithFactory


class TestSourcePackageRecipe(TestCaseWithFactory):
    """Tests for `SourcePackageRecipe` objects."""

    layer = DatabaseFunctionalLayer

    def makeSourcePackageRecipeFromBuilderRecipe(self, builder_recipe):
        """Make a SourcePackageRecipe from a recipe with arbitrary other data.
        """
        registrant = self.factory.makePerson()
        owner = self.factory.makeTeam(owner=registrant)
        distroseries = self.factory.makeDistroSeries()
        sourcepackagename = self.factory.makeSourcePackageName()
        name = self.factory.getUniqueString(u'recipe-name')
        return getUtility(ISourcePackageRecipeSource).new(
            registrant=registrant, owner=owner, distroseries=distroseries,
            sourcepackagename=sourcepackagename, name=name,
            builder_recipe=builder_recipe)

    def test_creation(self):
        # The metadata supplied when a SourcePackageRecipe is created is
        # present on the new object.
        registrant = self.factory.makePerson()
        owner = self.factory.makeTeam(owner=registrant)
        distroseries = self.factory.makeDistroSeries()
        sourcepackagename = self.factory.makeSourcePackageName()
        name = self.factory.getUniqueString(u'recipe-name')
        builder_recipe = self.factory.makeRecipe()
        recipe = getUtility(ISourcePackageRecipeSource).new(
            registrant=registrant, owner=owner, distroseries=distroseries,
            sourcepackagename=sourcepackagename, name=name,
            builder_recipe=builder_recipe)
        self.assertEquals(
            (registrant, owner, distroseries, sourcepackagename, name),
            (recipe.registrant, recipe.owner, recipe.distroseries,
             recipe.sourcepackagename, recipe.name))

    def test_source_implements_interface(self):
        # The SourcePackageRecipe class implements ISourcePackageRecipeSource.
        self.assertProvides(
            getUtility(ISourcePackageRecipeSource),
            ISourcePackageRecipeSource)

    def test_recipe_implements_interface(self):
        # SourcePackageRecipe objects implement ISourcePackageRecipe.
        recipe = self.makeSourcePackageRecipeFromBuilderRecipe(
            self.factory.makeRecipe())
        self.assertProvides(recipe, ISourcePackageRecipe)

    def test_branch_links_created(self):
        # When a recipe is created, we can query it for links to the branch
        # it references.
        branch = self.factory.makeAnyBranch()
        builder_recipe = self.factory.makeRecipe(branch)
        sp_recipe = self.makeSourcePackageRecipeFromBuilderRecipe(
            builder_recipe)
        self.assertEquals([branch], list(sp_recipe.getReferencedBranches()))

    def test_multiple_branch_links_created(self):
        # If a recipe links to more than one branch, getReferencedBranches()
        # returns all of them.
        branch1 = self.factory.makeAnyBranch()
        branch2 = self.factory.makeAnyBranch()
        builder_recipe = self.factory.makeRecipe(branch1, branch2)
        sp_recipe = self.makeSourcePackageRecipeFromBuilderRecipe(
            builder_recipe)
        self.assertEquals(
            sorted([branch1, branch2]),
            sorted(sp_recipe.getReferencedBranches()))

    def test_random_user_cant_edit(self):
        # An arbitrary user can't set attributes.
        branch1 = self.factory.makeAnyBranch()
        builder_recipe1 = self.factory.makeRecipe(branch1)
        sp_recipe = self.makeSourcePackageRecipeFromBuilderRecipe(
            builder_recipe1)
        branch2 = self.factory.makeAnyBranch()
        builder_recipe2 = self.factory.makeRecipe(branch2)
        login_person(self.factory.makePerson())
        self.assertRaises(
            Unauthorized, setattr, sp_recipe, 'builder_recipe',
            builder_recipe2)

    def test_set_recipe_text_resets_branch_references(self):
        # When the recipe_text is replaced, getReferencedBranches returns
        # (only) the branches referenced by the new recipe.
        branch1 = self.factory.makeAnyBranch()
        builder_recipe1 = self.factory.makeRecipe(branch1)
        sp_recipe = self.makeSourcePackageRecipeFromBuilderRecipe(
            builder_recipe1)
        branch2 = self.factory.makeAnyBranch()
        builder_recipe2 = self.factory.makeRecipe(branch2)
        login_person(sp_recipe.owner.teamowner)
        #import pdb; pdb.set_trace()
        sp_recipe.builder_recipe = builder_recipe2
        self.assertEquals([branch2], list(sp_recipe.getReferencedBranches()))

    def test_rejects_run_command(self):
        recipe_text = '''\
        # bzr-builder format 0.2 deb-version 0.1-{revno}
        %(base)s
        run touch test
        ''' % dict(base=self.factory.makeAnyBranch().bzr_identity)
        parser = RecipeParser(textwrap.dedent(recipe_text))
        builder_recipe = parser.parse()
        self.assertRaises(
            ForbiddenInstruction,
            self.makeSourcePackageRecipeFromBuilderRecipe, builder_recipe)

    def test_run_rejected_without_mangling_recipe(self):
        branch1 = self.factory.makeAnyBranch()
        builder_recipe1 = self.factory.makeRecipe(branch1)
        sp_recipe = self.makeSourcePackageRecipeFromBuilderRecipe(
            builder_recipe1)
        recipe_text = '''\
        # bzr-builder format 0.2 deb-version 0.1-{revno}
        %(base)s
        run touch test
        ''' % dict(base=self.factory.makeAnyBranch().bzr_identity)
        parser = RecipeParser(textwrap.dedent(recipe_text))
        builder_recipe2 = parser.parse()
        login_person(sp_recipe.owner.teamowner)
        self.assertRaises(
            ForbiddenInstruction, setattr, sp_recipe, 'builder_recipe',
            builder_recipe2)
        self.assertEquals([branch1], list(sp_recipe.getReferencedBranches()))

    def test_reject_newer_formats(self):
        builder_recipe = self.factory.makeRecipe()
        builder_recipe.format = 0.3
        self.assertRaises(
            TooNewRecipeFormat,
            self.makeSourcePackageRecipeFromBuilderRecipe, builder_recipe)

    def test_requestBuild(self):
        recipe = self.factory.makeSourcePackageRecipe()
        ppa = self.factory.makeArchive()
        distroseries = self.factory.makeDistroSeries()
        requester = self.factory.makePerson()
        build = recipe.requestBuild(ppa, distroseries, requester)
        # TODO: Fails as SourcePackageRecipeBuild doesn't correctly
        # implement the interface currently.
        #self.assertProvides(build, ISourcePackageRecipeBuild)
        self.assertEqual(build.archive, ppa)
        self.assertEqual(build.distroseries, distroseries)
        self.assertEqual(build.requester, requester)
        store = Store.of(build)
        store.flush()
        build_job = store.find(SourcePackageRecipeBuildJob,
                SourcePackageRecipeBuildJob.build_id==build.id).one()
        self.assertProvides(build_job, ISourcePackageRecipeBuildJob)
        self.assertTrue(build_job.virtualized)
        job = build_job.job
        self.assertProvides(job, IJob)
        self.assertEquals(job.status, JobStatus.WAITING)
        build_queue = store.find(BuildQueue, BuildQueue.job==job.id).one()
        self.assertProvides(build_queue, IBuildQueue)
        self.assertTrue(build_queue.virtualized)

    #def test_requestBuildRejectsNotPPA(self):
    #    builder_recipe = self.factory.makeSourcePackageRecipe()
    #    not_ppa = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
    #    self.assertRaises(builder_recipe.requestBuild, not_ppa)


class TestRecipeBranchRoundTripping(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestRecipeBranchRoundTripping, self).setUp()
        self.base_branch = self.factory.makeAnyBranch()
        self.nested_branch = self.factory.makeAnyBranch()
        self.merged_branch = self.factory.makeAnyBranch()
        self.branch_identities = {
            'base': self.base_branch.bzr_identity,
            'nested': self.nested_branch.bzr_identity,
            'merged': self.merged_branch.bzr_identity,
            }

    def get_recipe(self, recipe_text):
        builder_recipe = RecipeParser(textwrap.dedent(recipe_text)).parse()
        registrant = self.factory.makePerson()
        owner = self.factory.makeTeam(owner=registrant)
        distroseries = self.factory.makeDistroSeries()
        sourcepackagename = self.factory.makeSourcePackageName()
        name = self.factory.getUniqueString(u'recipe-name')
        recipe = getUtility(ISourcePackageRecipeSource).new(
            registrant=registrant, owner=owner, distroseries=distroseries,
            sourcepackagename=sourcepackagename, name=name,
            builder_recipe=builder_recipe)
        return recipe.builder_recipe

    def check_base_recipe_branch(self, branch, url, revspec=None,
            num_child_branches=0, revid=None, deb_version=None):
        self.check_recipe_branch(branch, None, url, revspec=revspec,
                num_child_branches=num_child_branches, revid=revid)
        self.assertEqual(deb_version, branch.deb_version)

    def check_recipe_branch(self, branch, name, url, revspec=None,
            num_child_branches=0, revid=None):
        self.assertEqual(name, branch.name)
        self.assertEqual(url, branch.url)
        self.assertEqual(revspec, branch.revspec)
        self.assertEqual(revid, branch.revid)
        self.assertEqual(num_child_branches, len(branch.child_branches))

    def test_builds_simplest_recipe(self):
        recipe_text = '''\
        # bzr-builder format 0.2 deb-version 0.1-{revno}
        %(base)s
        ''' % self.branch_identities
        base_branch = self.get_recipe(recipe_text)
        self.check_base_recipe_branch(
            base_branch, self.base_branch.bzr_identity,
            deb_version='0.1-{revno}')

    def test_builds_recipe_with_merge(self):
        recipe_text = '''\
        # bzr-builder format 0.2 deb-version 0.1-{revno}
        %(base)s
        merge bar %(merged)s
        ''' % self.branch_identities
        base_branch = self.get_recipe(recipe_text)
        self.check_base_recipe_branch(
            base_branch, self.base_branch.bzr_identity, num_child_branches=1,
            deb_version='0.1-{revno}')
        child_branch, location = base_branch.child_branches[0].as_tuple()
        self.assertEqual(None, location)
        self.check_recipe_branch(
            child_branch, "bar", self.merged_branch.bzr_identity)

    def test_builds_recipe_with_nest(self):
        recipe_text = '''\
        # bzr-builder format 0.2 deb-version 0.1-{revno}
        %(base)s
        nest bar %(nested)s baz
        ''' % self.branch_identities
        base_branch = self.get_recipe(recipe_text)
        self.check_base_recipe_branch(
            base_branch, self.base_branch.bzr_identity, num_child_branches=1,
            deb_version='0.1-{revno}')
        child_branch, location = base_branch.child_branches[0].as_tuple()
        self.assertEqual("baz", location)
        self.check_recipe_branch(
            child_branch, "bar", self.nested_branch.bzr_identity)

    def test_builds_recipe_with_nest_then_merge(self):
        recipe_text = '''\
        # bzr-builder format 0.2 deb-version 0.1-{revno}
        %(base)s
        nest bar %(nested)s baz
        merge zam %(merged)s
        ''' % self.branch_identities
        base_branch = self.get_recipe(recipe_text)
        self.check_base_recipe_branch(
            base_branch, self.base_branch.bzr_identity, num_child_branches=2,
            deb_version='0.1-{revno}')
        child_branch, location = base_branch.child_branches[0].as_tuple()
        self.assertEqual("baz", location)
        self.check_recipe_branch(
            child_branch, "bar", self.nested_branch.bzr_identity)
        child_branch, location = base_branch.child_branches[1].as_tuple()
        self.assertEqual(None, location)
        self.check_recipe_branch(
            child_branch, "zam", self.merged_branch.bzr_identity)

    def test_builds_recipe_with_merge_then_nest(self):
        recipe_text = '''\
        # bzr-builder format 0.2 deb-version 0.1-{revno}
        %(base)s
        merge zam %(merged)s
        nest bar %(nested)s baz
        ''' % self.branch_identities
        base_branch = self.get_recipe(recipe_text)
        self.check_base_recipe_branch(
            base_branch, self.base_branch.bzr_identity, num_child_branches=2,
            deb_version='0.1-{revno}')
        child_branch, location = base_branch.child_branches[0].as_tuple()
        self.assertEqual(None, location)
        self.check_recipe_branch(
            child_branch, "zam", self.merged_branch.bzr_identity)
        child_branch, location = base_branch.child_branches[1].as_tuple()
        self.assertEqual("baz", location)
        self.check_recipe_branch(
            child_branch, "bar", self.nested_branch.bzr_identity)

    def test_builds_a_merge_in_to_a_nest(self):
        recipe_text = '''\
        # bzr-builder format 0.2 deb-version 0.1-{revno}
        %(base)s
        nest bar %(nested)s baz
          merge zam %(merged)s
        ''' % self.branch_identities
        base_branch = self.get_recipe(recipe_text)
        self.check_base_recipe_branch(
            base_branch, self.base_branch.bzr_identity, num_child_branches=1,
            deb_version='0.1-{revno}')
        child_branch, location = base_branch.child_branches[0].as_tuple()
        self.assertEqual("baz", location)
        self.check_recipe_branch(
            child_branch, "bar", self.nested_branch.bzr_identity,
            num_child_branches=1)
        child_branch, location = child_branch.child_branches[0].as_tuple()
        self.assertEqual(None, location)
        self.check_recipe_branch(
            child_branch, "zam", self.merged_branch.bzr_identity)

    def tests_builds_nest_into_a_nest(self):
        nested2 = self.factory.makeAnyBranch()
        self.branch_identities['nested2'] = nested2.bzr_identity
        recipe_text = '''\
        # bzr-builder format 0.2 deb-version 0.1-{revno}
        %(base)s
        nest bar %(nested)s baz
          nest zam %(nested2)s zoo
        ''' % self.branch_identities
        base_branch = self.get_recipe(recipe_text)
        self.check_base_recipe_branch(
            base_branch, self.base_branch.bzr_identity, num_child_branches=1,
            deb_version='0.1-{revno}')
        child_branch, location = base_branch.child_branches[0].as_tuple()
        self.assertEqual("baz", location)
        self.check_recipe_branch(
            child_branch, "bar", self.nested_branch.bzr_identity,
            num_child_branches=1)
        child_branch, location = child_branch.child_branches[0].as_tuple()
        self.assertEqual("zoo", location)
        self.check_recipe_branch(child_branch, "zam", nested2.bzr_identity)

    def tests_builds_recipe_with_revspecs(self):
        recipe_text = '''\
        # bzr-builder format 0.2 deb-version 0.1-{revno}
        %(base)s revid:a
        nest bar %(nested)s baz tag:b
        merge zam %(merged)s 2
        ''' % self.branch_identities
        base_branch = self.get_recipe(recipe_text)
        self.check_base_recipe_branch(
            base_branch, self.base_branch.bzr_identity, num_child_branches=2,
            revspec="revid:a", deb_version='0.1-{revno}')
        instruction = base_branch.child_branches[0]
        child_branch = instruction.recipe_branch
        location = instruction.nest_path
        self.assertEqual("baz", location)
        self.check_recipe_branch(
            child_branch, "bar", self.nested_branch.bzr_identity,
            revspec="tag:b")
        child_branch, location = base_branch.child_branches[1].as_tuple()
        self.assertEqual(None, location)
        self.check_recipe_branch(
            child_branch, "zam", self.merged_branch.bzr_identity, revspec="2")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

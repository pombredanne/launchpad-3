# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation of the recipe storage.

This is purely an implementation detail of SourcePackageRecipe.recipe_text and
SourcePackageRecipeBuild.manifest, the classes in this file have no public
interfaces.
"""

__metaclass__ = type
__all__ = []

from bzrlib.plugins.builder.recipe import RecipeParser

from storm.locals import Int, Reference, Storm, Unicode

from zope.component import getUtility

from canonical.launchpad.interfaces.lpstorm import IStore

from lp.code.model.branch import Branch
from lp.code.interfaces.branch import IBranchSet


class _SourcePackageRecipeDataBranch(Storm):
    """The link between a SourcePackageRecipeData row and a Branch row."""

    __storm_table__ = "SourcePackageRecipeDataBranch"

    id = Int(primary=True)

    branch_id = Int(name='branch', allow_none=False)
    branch = Reference(branch_id, 'Branch.id')

    sourcepackagerecipedata_id = Int(
        name='sourcepackagerecipedata', allow_none=False)
    sourcepackagerecipedata = Reference(
        sourcepackagerecipedata_id, '_SourcePackageRecipeData.id')

    def __init__(self, sprd, branch):
        self.sourcepackagerecipedata = sprd
        self.branch = branch


def walk_branch_urls(branch):
    """Yield every branch url referenced by `branch` and its children.

    :param branch: A `bzrlib.plugins.builder.recipe.RecipeBranch` object.
    """
    # Possibly this should/could be in bzr-builder?
    # Possibly should/could have direct tests?
    yield branch.url
    for child_branch in branch.child_branches:
        for url in walk_branch_urls(child_branch.recipe_branch):
            yield url


class _SourcePackageRecipeData(Storm):
    """Essentially, the text of a bzr-builder recipe but with added data.
    """

    __storm_table__ = "SourcePackageRecipeData"

    id = Int(primary=True)

    _recipe = Unicode(name='recipe')

    # For now, we just store the recipe verbatim.  Soon, we'll want to rewrite
    # the recipe to replace the branch urls with something that references the
    # _SourcePackageRecipeDataBranch linking table on write and vice versa on
    # read.

    def _get_recipe(self):
        """The text of the recipe."""
        return self._recipe

    def _set_recipe(self, recipe):
        """Set the text of the recipe."""
        IStore(self).find(
            _SourcePackageRecipeDataBranch,
            _SourcePackageRecipeDataBranch.sourcepackagerecipedata == self
            ).remove()
        base_branch = RecipeParser(recipe).parse()
        db_branches = []
        for url in walk_branch_urls(base_branch):
            db_branches.append(getUtility(IBranchSet).getByUrl(url))
        for db_branch in db_branches:
            _SourcePackageRecipeDataBranch(self, db_branch)
        self._recipe = recipe

    recipe = property(_get_recipe, _set_recipe)

    def __init__(self, recipe):
        """Initialize the object from the recipe text."""
        self.recipe = recipe

    def getReferencedBranches(self):
        """Return an iterator of the Branch objects referenced by this recipe.
        """
        return IStore(self).find(
            Branch,
            _SourcePackageRecipeDataBranch.sourcepackagerecipedata == self,
            Branch.id == _SourcePackageRecipeDataBranch.branch_id)

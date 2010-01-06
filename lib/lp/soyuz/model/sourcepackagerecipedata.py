# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation of the recipe storage.

This is purely an implementation detail of SourcePackageRecipe.recipe_text and
SourcePackageRecipeBuild.manifest, the classes in this file have no public
interfaces.
"""

__metaclass__ = type
__all__ = ['_SourcePackageRecipeData']

from bzrlib.plugins.builder.recipe import RecipeParser

from storm.locals import Int, Reference, Storm, Unicode

from zope.component import getUtility

from canonical.launchpad.interfaces.lpstorm import IStore

from lp.code.model.branch import Branch
from lp.code.interfaces.branch import IBranchSet


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
        1/0

    recipe = property(_get_recipe, _set_recipe)

    def __init__(self, recipe):
        """Initialize the object from the recipe text."""
        #self.recipe = recipe

    def getReferencedBranches(self):
        """Return an iterator of the Branch objects referenced by this recipe.
        """
        return IStore(self).find(
            Branch,
            _SourcePackageRecipeDataBranch.sourcepackagerecipedata == self,
            Branch.id == _SourcePackageRecipeDataBranch.branch_id)

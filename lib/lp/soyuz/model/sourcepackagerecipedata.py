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
from lp.code.interfaces.branchlookup import IBranchLookup


class _SourcePackageRecipeDataInstruction(Storm):
    """XXX."""

    __storm_table__ = "SourcePackageRecipeDataInstruction"

    id = Int(primary=True)


class _SourcePackageRecipeData(Storm):
    """XXX."""

    __storm_table__ = "SourcePackageRecipeData"

    id = Int(primary=True)

    base_branch_id = Int(name='base_branch', allow_none=False)
    base_branch = Reference(base_branch_id, 'Branch.id')

    recipe_format = Unicode(allow_none=False)
    deb_version_template = Unicode(allow_none=False)

    def getRecipe(self):
        """The text of the recipe."""
        1/0

    def setRecipe(self, recipe):
        """Set the text of the recipe."""
        base_branch = RecipeParser(recipe).parse()
        branch_lookup = getUtility(IBranchLookup)
        self.base_branch = branch_lookup.getByUrl(base_branch.url)
        self.deb_version_template = base_branch.deb_version
        self.recipe_format = unicode(base_branch.format)

    def __init__(self, recipe):
        """Initialize the object from the recipe text."""
        self.setRecipe(recipe)

    def getReferencedBranches(self):
        """Return an iterator of the Branch objects referenced by this recipe.
        """
        return IStore(self).find(
            Branch,
            _SourcePackageRecipeDataBranch.sourcepackagerecipedata == self,
            Branch.id == _SourcePackageRecipeDataBranch.branch_id)

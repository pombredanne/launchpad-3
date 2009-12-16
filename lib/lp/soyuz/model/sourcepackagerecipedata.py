# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Module docstring goes here."""

__metaclass__ = type
__all__ = []

from bzrlib.plugins.builder.recipe import RecipeParser

from storm.locals import Int, Reference, Store, Storm, Unicode

from zope.component import getUtility

from canonical.launchpad.interfaces.lpstorm import IStore

from lp.code.model.branch import Branch
from lp.code.interfaces.branch import IBranchSet



class _SourcePackageRecipeDataBranch(Storm):
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


class _SourcePackageRecipeData(Storm):

    __storm_table__ = "SourcePackageRecipeData"

    id = Int(primary=True)

    _recipe = Unicode(name='recipe')

    # Maybe all this stuff should just be on the containing object...

    def _get_recipe(self):
        # Read recipe text out, rewrite branch references.
        pass

    def _set_recipe(self, recipe):
        # Read recipe text out, rewrite branch references.
        base_branch = RecipeParser(recipe).parse()
        b = getUtility(IBranchSet).getByUrl(base_branch.url)
        _SourcePackageRecipeDataBranch(self, b)
        self._recipe = recipe

    recipe = property(_get_recipe, _set_recipe)

    def __init__(self, recipe):
        self.recipe = recipe

    @property
    def referenced_branches(self):
        return IStore(self).find(
            Branch,
            _SourcePackageRecipeDataBranch.sourcepackagerecipedata == self,
            Branch.id == _SourcePackageRecipeDataBranch.branch_id)

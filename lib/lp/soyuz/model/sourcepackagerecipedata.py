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

from canonical.database.enumcol import EnumCol
from canonical.launchpad.interfaces.lpstorm import IStore

from lp.code.model.branch import Branch
from lp.code.interfaces.branchlookup import IBranchLookup


class _SourcePackageRecipeDataInstruction(Storm):
    """XXX."""

    __storm_table__ = "SourcePackageRecipeDataInstruction"

    def __init__(self, name, type, comment, line_number, branch, revspec,
                 directory, recipe, parent_instruction):
        self.name = name
        self.type = type
        self.comment = comment
        self.line_number = line_number
        self.branch = branch
        self.revspec = revspec
        self.directory = directory
        self.recipe = recipe
        self.parent_instruction = parent_instruction

    id = Int(primary=True)

    name = Unicode(allow_none=False)
    # Should be an EnumCol
    type = Int(allow_none=True)
    comment = Unicode(allow_none=True)
    line_number = Int(allow_none=False)

    branch_id = Int(name='branch', allow_none=False)
    branch = Reference(branch_id, 'Branch.id')

    revspec = Unicode(allow_none=True)
    directory = Unicode(allow_none=True)

    recipe_id = Int(name='recipe', allow_none=False)
    recipe = Reference(recipe_id, '_SourcePackageRecipeData.id')

    parent_instruction_id = Int(name='parent_instruction', allow_none=True)
    parent_instruction = Reference(
        parent_instruction_id, '_SourcePackageRecipeDataInstruction.id')


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

    def _record_instructions(self, branch, parent_insn):
        for b in branch.child_branches:
            db_branch = getUtility(IBranchLookup).getByUrl(b.recipe_branch.url)
            type = 1
            comment = None
            line_number = 0
            insn = _SourcePackageRecipeDataInstruction(
                b.recipe_branch.name, type, comment, line_number, db_branch,
                b.recipe_branch.revspec, b.nest_path, self, parent_insn)
            self._record_instructions(b.recipe_branch, insn)

    def setRecipe(self, builder_recipe):
        """Set the text of the recipe."""
        IStore(self).find(
            _SourcePackageRecipeDataInstruction,
            _SourcePackageRecipeDataInstruction.recipe == self).remove()
        branch_lookup = getUtility(IBranchLookup)
        base_branch = builder_recipe
        self.base_branch = branch_lookup.getByUrl(base_branch.url)
        self.deb_version_template = base_branch.deb_version
        self.recipe_format = unicode(base_branch.format)
        self._record_instructions(base_branch, None)

    def __init__(self, recipe):
        """Initialize the object from the recipe text."""
        self.setRecipe(recipe)

    def getReferencedBranches(self):
        """Return an iterator of the Branch objects referenced by this recipe.
        """
        yield self.base_branch
        sub_branches = IStore(self).find(
            Branch,
            _SourcePackageRecipeDataInstruction.recipe == self,
            Branch.id == _SourcePackageRecipeDataInstruction.branch_id)
        for branch in sub_branches:
            yield branch

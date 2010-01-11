# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation of the recipe storage.

This is purely an implementation detail of SourcePackageRecipe.recipe_data and
SourcePackageRecipeBuild.manifest, the classes in this file have no public
interfaces.
"""

__metaclass__ = type
__all__ = ['_SourcePackageRecipeData']

from bzrlib.plugins.builder.recipe import BaseRecipeBranch, RecipeBranch

from lazr.enum import DBEnumeratedType, DBItem

from storm.locals import Int, Reference, ReferenceSet, Storm, Unicode

from zope.component import getUtility

from canonical.database.enumcol import EnumCol
from canonical.launchpad.interfaces.lpstorm import IStore

from lp.code.model.branch import Branch
from lp.code.interfaces.branchlookup import IBranchLookup


class InstructionType(DBEnumeratedType):

    MERGE = DBItem(1, """
        Merge instruction

        A merge instruction.""")

    NEST = DBItem(2, """
        Nest instruction

        A nest instruction.""")


class _SourcePackageRecipeDataInstruction(Storm):
    """XXX."""

    __storm_table__ = "SourcePackageRecipeDataInstruction"

    def __init__(self, name, type, comment, line_number, branch, revspec,
                 directory, recipe_data, parent_instruction):
        self.name = unicode(name)
        self.type = type
        self.comment = comment
        self.line_number = line_number
        self.branch = branch
        if revspec is not None:
            revspec = unicode(revspec)
        self.revspec = revspec
        if directory is not None:
            directory = unicode(directory)
        self.directory = directory
        self.recipe_data = recipe_data
        self.parent_instruction = parent_instruction

    id = Int(primary=True)

    name = Unicode(allow_none=False)
    type = EnumCol(notNull=True, schema=InstructionType)
    comment = Unicode(allow_none=True)
    line_number = Int(allow_none=False)

    branch_id = Int(name='branch', allow_none=False)
    branch = Reference(branch_id, 'Branch.id')

    revspec = Unicode(allow_none=True)
    directory = Unicode(allow_none=True)

    recipe_data_id = Int(name='recipe_data', allow_none=False)
    recipe_data = Reference(recipe_data_id, '_SourcePackageRecipeData.id')

    parent_instruction_id = Int(name='parent_instruction', allow_none=True)
    parent_instruction = Reference(
        parent_instruction_id, '_SourcePackageRecipeDataInstruction.id')

    def append_to_recipe(self, recipe_branch):
        branch = RecipeBranch(
            self.name, self.branch.bzr_identity, self.revspec)
        if self.type == InstructionType.MERGE:
            recipe_branch.merge_branch(branch)
        elif self.type == InstructionType.NEST:
            recipe_branch.nest_branch(self.directory, branch)
        else:
            raise AssertionError("Unknown type %r" % self.type)


class _SourcePackageRecipeData(Storm):
    """XXX."""

    __storm_table__ = "SourcePackageRecipeData"

    id = Int(primary=True)

    base_branch_id = Int(name='base_branch', allow_none=False)
    base_branch = Reference(base_branch_id, 'Branch.id')

    recipe_format = Unicode(allow_none=False)
    deb_version_template = Unicode(allow_none=False)
    revspec = Unicode(allow_none=True)

    instructions = ReferenceSet(
        id, _SourcePackageRecipeDataInstruction.recipe_data_id,
        order_by=_SourcePackageRecipeDataInstruction.line_number)

    def getRecipe(self):
        """The BaseRecipeBranch version of the recipe."""
        base_branch = BaseRecipeBranch(
            self.base_branch.bzr_identity, self.deb_version_template,
            self.recipe_format, self.revspec)
        for instruction in self.instructions:
            instruction.append_to_recipe(base_branch)
        return base_branch

    def _record_instructions(self, branch, parent_insn):
        for b in branch.child_branches:
            db_branch = getUtility(IBranchLookup).getByUrl(b.recipe_branch.url)
            type = InstructionType.MERGE
            comment = None
            line_number = 0
            insn = _SourcePackageRecipeDataInstruction(
                b.recipe_branch.name, type, comment, line_number, db_branch,
                b.recipe_branch.revspec, b.nest_path, self, parent_insn)
            self._record_instructions(b.recipe_branch, insn)

    def setRecipe(self, builder_recipe):
        """Convert the BaseRecipeBranch `builder_recipe` to the db form."""
        # XXX Why doesn't self.instructions.clear() work?
        IStore(self).find(
            _SourcePackageRecipeDataInstruction,
            _SourcePackageRecipeDataInstruction.recipe_data == self).remove()
        branch_lookup = getUtility(IBranchLookup)
        base_branch = builder_recipe
        self.base_branch = branch_lookup.getByUrl(base_branch.url)
        self.deb_version_template = unicode(base_branch.deb_version)
        self.recipe_format = unicode(base_branch.format)
        if builder_recipe.revspec is not None:
            self.revspec = unicode(self.revspec)
        self._record_instructions(base_branch, None)

    def __init__(self, recipe):
        """Initialize the object from the BaseRecipeBranch."""
        self.setRecipe(recipe)

    def getReferencedBranches(self):
        """Return an iterator of the Branch objects referenced by this recipe.
        """
        yield self.base_branch
        sub_branches = IStore(self).find(
            Branch,
            _SourcePackageRecipeDataInstruction.recipe_data == self,
            Branch.id == _SourcePackageRecipeDataInstruction.branch_id)
        for branch in sub_branches:
            yield branch

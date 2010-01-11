# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation of the recipe storage.

This is purely an implementation detail of SourcePackageRecipe.recipe_data and
SourcePackageRecipeBuild.manifest, the classes in this file have no public
interfaces.
"""

__metaclass__ = type
__all__ = ['_SourcePackageRecipeData']

from bzrlib.plugins.builder.recipe import (
    BaseRecipeBranch, MergeInstruction, NestInstruction, RecipeBranch)

from lazr.enum import DBEnumeratedType, DBItem

from storm.locals import Int, Reference, ReferenceSet, Storm, Unicode

from zope.component import getUtility

from canonical.database.enumcol import EnumCol
from canonical.launchpad.interfaces.lpstorm import IStore

from lp.code.model.branch import Branch
from lp.code.interfaces.branchlookup import IBranchLookup
from lp.soyuz.interfaces.sourcepackagerecipe import ForbiddenInstruction


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
        return branch


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
        insn_stack = []
        for insn in self.instructions:
            while insn_stack and insn_stack[-1]['insn'] != insn.parent_instruction:
                insn_stack.pop()
            if insn_stack:
                target_branch = insn_stack[-1]['recipe_branch']
            else:
                target_branch = base_branch
            recipe_branch = insn.append_to_recipe(target_branch)
            insn_stack.append(
                dict(insn=insn, recipe_branch=recipe_branch))
        return base_branch

    def _scan_instructions(self, branch, parent_insn, record=False,
                             line_number=0):
        """XXX."""
        for instruction in branch.child_branches:
            if isinstance(instruction, MergeInstruction):
                type = InstructionType.MERGE
            elif isinstance(instruction, NestInstruction):
                type = InstructionType.NEST
            elif not record:
                raise ForbiddenInstruction(str(instruction))
            else:
                raise AssertionError(
                    "Unsupported instruction %r" % instruction)
            line_number += 1
            if record:
                comment = None
                db_branch = getUtility(IBranchLookup).getByUrl(
                    instruction.recipe_branch.url)
                insn = _SourcePackageRecipeDataInstruction(
                    instruction.recipe_branch.name, type, comment,
                    line_number, db_branch, instruction.recipe_branch.revspec,
                    instruction.nest_path, self, parent_insn)
            else:
                insn = None
            line_number = self._scan_instructions(
                instruction.recipe_branch, insn, record, line_number)
        return line_number

    def setRecipe(self, builder_recipe):
        """Convert the BaseRecipeBranch `builder_recipe` to the db form."""
        # XXX don't destroy everything until we know there's no run command?
        # XXX Why doesn't self.instructions.clear() work?
        self._scan_instructions(
            builder_recipe, parent_insn=None)
        IStore(self).find(
            _SourcePackageRecipeDataInstruction,
            _SourcePackageRecipeDataInstruction.recipe_data == self).remove()
        branch_lookup = getUtility(IBranchLookup)
        self.base_branch = branch_lookup.getByUrl(builder_recipe.url)
        self.deb_version_template = unicode(builder_recipe.deb_version)
        self.recipe_format = unicode(builder_recipe.format)
        if builder_recipe.revspec is not None:
            self.revspec = unicode(builder_recipe.revspec)
        self._scan_instructions(
            builder_recipe, parent_insn=None, record=True)

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

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


import os.path
import lp.codehosting
from bzrlib.plugins import builder


class BuildRecipe:

    def __init__(self, work_dir):
        self.work_dir = work_dir

    def buildTree(self, recipe_text, suite):
        tree_path = os.path.join(self.work_dir, 'tree')
        os.mkdir(tree_path)
        changed, base_branch = builder.get_prepared_branch_from_recipe(
            recipe_text)
        builder.build_tree(base_branch, tree_path)

    def installBuildDeps(self):
        pass

    def buildSourcePackage(self):
        pass

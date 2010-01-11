# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


import os.path
import lp.codehosting
from bzrlib.plugins import builder
from bzrlib.plugins.builder import recipe


class BuildRecipe:

    def __init__(self, recipe_text, author_name, author_email, work_dir,
                 package_name, suite):
        self.recipe_text = recipe_text
        self.author_name = author_name
        self.author_email = author_email
        self.work_dir = work_dir
        self.package_name = package_name
        self.suite = suite
        self.tree_path = None
        self.base_branch = None

    def buildTree(self):
        changed, self.base_branch = builder.get_prepared_branch_from_recipe(
            self.recipe_text)
        tree_path = builder.calculate_package_dir(self.base_branch,
                                                  self.package_name,
                                                  self.work_dir)
        self.tree_path = tree_path
        os.mkdir(tree_path)
        builder.build_tree(self.base_branch, tree_path)
        builder.add_changelog_entry(self.base_branch, tree_path,
                                    distribution=self.suite,
                                    package=self.package_name,
                                    author_name=self.author_name,
                                    author_email=self.author_email)

    def installBuildDeps(self):
        pass

    def buildSourcePackage(self):
        builder.build_source_package(self.tree_path)

    def writeManifest(self):
        manifest_path = os.path.join(self.work_dir, 'manifest')
        builder.write_manifest_to_path(manifest_path, self.base_branch)

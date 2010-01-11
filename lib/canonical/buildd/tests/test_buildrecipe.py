# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).


__metaclass__ = type


import os
import unittest

from bzrlib.tests import TestCaseWithTransport
from canonical.buildd.buildrecipe import BuildRecipe

STD_HEADER = "# bzr-builder format 0.2 deb-version farblesnitch\n"
EXAMPLE_RECIPE = STD_HEADER + "foo\n"


class TestBuildRecipe(TestCaseWithTransport):

    def test_build_recipe(self):
        tree = self.make_branch_and_tree('foo')
        self.build_tree_contents([('foo/README', 'example')])
        tree.add('README')
        tree.commit('add readme')

        os.mkdir('work')
        BuildRecipe('work').buildTree(EXAMPLE_RECIPE, 'suite')
        self.failUnlessExists('work/tree')
        self.assertFileEqual('example', 'work/tree/README')



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

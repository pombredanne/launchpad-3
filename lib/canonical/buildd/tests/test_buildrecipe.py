# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).


from __future__ import with_statement


__metaclass__ = type


import os
import unittest

from bzrlib.tests import TestCaseWithTransport
from canonical.buildd.buildrecipe import BuildRecipe

STD_HEADER = "# bzr-builder format 0.2 deb-version farblesnitch\n"
EXAMPLE_RECIPE = STD_HEADER + "foo\n"
EXAMPLE_MANIFEST = STD_HEADER + "foo revid:rev1\n"
EXAMPLE_RULES = '#!/usr/bin/make -f\nclean:\n'
EXAMPLE_CONTROL = (
    "Source: foo-la\n"
    "Maintainer: Somebody <me@example.com>\n"
    "Build-Depends: debhelper\n\n"
    "Package: foo-la\n"
    "Architechture: all\n"
    "Description: foo\n")


class TestBuildRecipe(TestCaseWithTransport):

    def makeExampleRecipe(self):
        tree = self.make_branch_and_tree('foo')
        self.build_tree_contents([('foo/README', 'example'),
                                  ('foo/debian/',),
                                  ('foo/debian/rules', EXAMPLE_RULES),
                                  ('foo/debian/control', EXAMPLE_CONTROL)])
        tree.add(['README', 'debian', 'debian/rules', 'debian/control'])
        tree.commit('add readme', rev_id='rev1')
        os.mkdir('work')
        return BuildRecipe(EXAMPLE_RECIPE, 'Author Name',
                           'author@example.com', 'work', 'foo-la', 'suite')

    def test_buildTree(self):
        recipe = self.makeExampleRecipe()
        recipe.buildTree()
        self.failUnlessExists(recipe.tree_path)
        self.assertFileEqual('example',
                             os.path.join(recipe.tree_path, 'README'))
        # Ensure first line of the changelog includes the information we
        # passed in.
        with open(os.path.join(recipe.tree_path, 'debian/changelog')) as cl:
            lines = cl.readlines()
        self.assertContainsRe(lines[0], '^foo-la \(farblesnitch\) suite;')
        self.assertContainsRe(lines[-2],
                              '^ -- Author Name <author@example.com>  ')

    def test_writeManifest(self):
        recipe = self.makeExampleRecipe()
        recipe.buildTree()
        recipe.writeManifest()
        self.assertFileEqual(EXAMPLE_MANIFEST, 'work/manifest')

    def test_buildSourcePackage(self):
        recipe = self.makeExampleRecipe()
        recipe.buildTree()
        recipe.buildSourcePackage()
        self.failUnlessExists('work/foo-la_farblesnitch_source.changes')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

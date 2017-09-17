# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import errno
import os
import tarfile

from bzrlib.bzrdir import BzrDir

from lp.testing import TestCase
from lp.translations.pottery.detect_intltool import is_intltool_structure


class SetupTestPackageMixin:

    test_data_dir = "pottery_test_data"

    def prepare_package(self, packagename, buildfiles=None):
        """Unpack the specified package in a temporary directory.

        Change into the package's directory.

        :param packagename: The name of the package to prepare.
        :param buildfiles: A dictionary of path:content describing files to
            add to the package.
        """
        # First build the path for the package.
        packagepath = os.path.join(
            os.getcwd(), os.path.dirname(__file__),
            self.test_data_dir, packagename + ".tar.bz2")
        # Then change into the temporary directory and unpack it.
        self.useTempDir()
        with tarfile.open(packagepath, "r|bz2") as tar:
            tar.extractall()
        os.chdir(packagename)

        if buildfiles is None:
            return

        # Add files as requested.
        for path, content in buildfiles.items():
            directory = os.path.dirname(path)
            if directory != '':
                try:
                    os.makedirs(directory)
                except OSError as e:
                    # Doesn't matter if it already exists.
                    if e.errno != errno.EEXIST:
                        raise
            with open(path, 'w') as the_file:
                the_file.write(content)


class TestDetectIntltoolInBzrTree(TestCase, SetupTestPackageMixin):

    def prepare_tree(self):
        return BzrDir.create_standalone_workingtree(".")

    def test_detect_intltool_structure(self):
        # Detect a simple intltool structure.
        self.prepare_package("intltool_POTFILES_in_1")
        tree = self.prepare_tree()
        self.assertTrue(is_intltool_structure(tree))

    def test_detect_no_intltool_structure(self):
        # If no POTFILES.in exists, no intltool structure is assumed.
        self.prepare_package("intltool_POTFILES_in_1")
        os.remove("./po-intltool/POTFILES.in")
        tree = self.prepare_tree()
        self.assertFalse(is_intltool_structure(tree))

    def test_detect_intltool_structure_module(self):
        # Detect an intltool structure in subdirectories.
        self.prepare_package("intltool_POTFILES_in_2")
        tree = self.prepare_tree()
        self.assertTrue(is_intltool_structure(tree))

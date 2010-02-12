# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os
import shutil
import tarfile
import tempfile
import unittest

from StringIO import StringIO
from textwrap import dedent

from bzrlib.workingtree import WorkingTree
from canonical.launchpad.scripts.tests import run_script
from lp.translations.pottery.detect_intltool import (
    ConfigFile, check_potfiles_in, find_intltool_dirs, find_potfiles_in,
    get_translation_domain, is_intltool_structure)
from lp.testing import TestCase


class SetupTestPackageMixin(object):

    def init_working_directory(self):
        """Create temporary working directory."""
        self.curdir = os.getcwd()
        self.testdir = os.path.join(self.curdir, os.path.dirname(__file__))
        self.workdir = tempfile.mkdtemp()
        os.chdir(self.workdir)

    def remove_working_directory(self):
        """Remove temporary directory and all its content."""
        os.chdir(self.curdir)
        shutil.rmtree(self.workdir)

    def prepare_package(self, packagename):
        """Unpack the specified package and change into its directory."""
        packagepath = os.path.join(self.testdir, packagename+".tar.bz2")
        tar = tarfile.open(packagepath, "r:bz2")
        tar.extractall()
        tar.close()
        os.chdir(packagename)


class TestDetectIntltool(TestCase, SetupTestPackageMixin):

    def setUp(self):
        super(TestDetectIntltool, self).setUp()
        self.init_working_directory()

    def tearDown(self):
        self.remove_working_directory()
        super(TestDetectIntltool, self).tearDown()

    def test_detect_potfiles_in(self):
        # Find POTFILES.in in a package with multiple dirs when only one has
        # POTFILES.in.
        self.prepare_package("intltool_POTFILES_in_1")
        dirs = find_potfiles_in()
        self.assertContentEqual(["./po-intltool"], dirs)

    def test_detect_potfiles_in_module(self):
        # Find POTFILES.in in a package with POTFILES.in at different levels.
        self.prepare_package("intltool_POTFILES_in_2")
        dirs = find_potfiles_in()
        self.assertContentEqual(["./po", "./module1/po"], dirs)

    def test_check_potfiles_in_content_ok(self):
        # Ideally all files listed in POTFILES.in exist in the source package.
        self.prepare_package("intltool_single_ok")
        self.assertTrue(check_potfiles_in("./po")) 

    def test_check_potfiles_in_content_ok_file_added(self):
        # If a file is not listed in POTFILES.in, the file is still good for
        # our purposes.
        self.prepare_package("intltool_single_ok")
        added_file = file("./src/sourcefile_new.c", "w")
        added_file.write("/* Test file. */")
        added_file.close()
        self.assertTrue(check_potfiles_in("./po")) 

    def test_check_potfiles_in_content_not_ok_file_removed(self):
        # If a file is missing that is listed in POTFILES.in, the file
        # intltool structure is probably broken and cannot be used for
        # our purposes.
        self.prepare_package("intltool_single_ok")
        os.remove("./src/sourcefile1.c")
        self.assertFalse(check_potfiles_in("./po")) 

    def test_check_potfiles_in_wrong_directory(self):
        # Passing in the wrong directory will cause the check to fail
        # gracefully and return False.
        self.prepare_package("intltool_single_ok")
        self.assertFalse(check_potfiles_in("./foo")) 

    def test_find_intltool_dirs(self):
        # Complete run: find all directories with intltool structure.
        self.prepare_package("intltool_full_ok")
        self.assertEqual(
            ["./po-module1", "./po-module2"], find_intltool_dirs())

    def test_find_intltool_dirs_broken(self):
        # Complete run: part of the intltool structure is broken.
        self.prepare_package("intltool_full_ok")
        os.remove("./src/module1/sourcefile1.c")
        self.assertEqual(
            ["./po-module2"], find_intltool_dirs())

    def test_get_translation_domain_makevars(self):
        # Find a translation domain in Makevars.
        self.prepare_package("intltool_domain_makevars")
        self.assertEqual(
            "translationdomain",
            get_translation_domain("po"))

    def test_get_translation_domain_makefile_in_in(self):
        # Find a translation domain in Makefile.in.in.
        self.prepare_package("intltool_domain_makefile_in_in")
        self.assertEqual(
            "packagename-in-in",
            get_translation_domain("po"))

    def test_get_translation_domain_configure_ac(self):
        # Find a translation domain in configure.ac.
        self.prepare_package("intltool_domain_configure_ac")
        self.assertEqual(
            "packagename-ac",
            get_translation_domain("po"))

    def test_get_translation_domain_configure_in(self):
        # Find a translation domain in configure.in.
        self.prepare_package("intltool_domain_configure_in")
        self.assertEqual(
            "packagename-in",
            get_translation_domain("po"))

    def test_get_translation_domain_makefile_in_in_substitute(self):
        # Find a translation domain in Makefile.in.in with substitution from
        # configure.ac.
        self.prepare_package("intltool_domain_makefile_in_in_substitute")
        self.assertEqual(
            "domainname-ac-in-in",
            get_translation_domain("po"))

    def test_get_translation_domain_makefile_in_in_substitute_same_name(self):
        # Find a translation domain in Makefile.in.in with substitution from
        # configure.ac from a variable with the same name as in
        # Makefile.in.in.
        self.prepare_package(
            "intltool_domain_makefile_in_in_substitute_same_name")
        self.assertEqual(
            "packagename-ac-in-in",
            get_translation_domain("po"))

    def test_get_translation_domain_makefile_in_in_substitute_same_file(self):
        # Find a translation domain in Makefile.in.in with substitution from
        # the same file.
        self.prepare_package(
            "intltool_domain_makefile_in_in_substitute_same_file")
        self.assertEqual(
            "domain-in-in-in-in",
            get_translation_domain("po"))

    def test_get_translation_domain_makefile_in_in_substitute_broken(self):
        # Find no translation domain in Makefile.in.in when the substitution
        # cannot be fulfilled.
        self.prepare_package(
            "intltool_domain_makefile_in_in_substitute_broken")
        self.assertIs(None, get_translation_domain("po"))

    def test_get_translation_domain_configure_in_substitute_version(self):
        # Find a translation domain in configure.in with Makefile-style
        # substitution from the same file.
        self.prepare_package(
            "intltool_domain_configure_in_substitute_version")
        self.assertEqual(
            "domainname-in42",
            get_translation_domain("po"))

    def test_pottery_check_intltool_script(self):
        # Let the script run to see it works fine.
        self.prepare_package("intltool_full_ok")

        return_code, stdout, stderr = run_script(
            'scripts/rosetta/pottery-check-intltool.py', [])

        self.assertEqual(dedent("""\
            ./po-module1 (packagename-module1)
            ./po-module2 (packagename-module2)
            """), stdout)


class TestDetectIntltoolInBzrTree(TestCase, SetupTestPackageMixin):

    def setUp(self):
        super(TestDetectIntltoolInBzrTree, self).setUp()
        self.init_working_directory()

    def tearDown(self):
        self.remove_working_directory()
        super(TestDetectIntltoolInBzrTree, self).tearDown()

    def prepare_tree(self):
        os.system("bzr init")
        os.system("bzr add")
        os.system("bzr commit -m Initial")
        return WorkingTree.open(".")

    def test_detect_potfiles_in(self):
        # Find POTFILES.in in a package with multiple dirs when only one has
        # POTFILES.in.
        self.prepare_package("intltool_POTFILES_in_1")
        tree = self.prepare_tree()
        self.assertTrue(is_intltool_structure(tree))

    def test_detect_potfiles_in_module(self):
        # Find POTFILES.in in a package with POTFILES.in at different levels.
        self.prepare_package("intltool_POTFILES_in_2")
        tree = self.prepare_tree()
        self.assertTrue(is_intltool_structure(tree))


class TestConfigFile(TestCase):

    def setUp(self):
        super(TestConfigFile, self).setUp()
        self.configfile = ConfigFile(StringIO(dedent("""\
            # Demo config file
            CCC
            AAA=
            BBB = 
            CCC = ccc # comment
            DDD=dd.d
            """)))

    def test_getVariable_exists(self):
        self.assertEqual('ccc', self.configfile.getVariable('CCC'))
        self.assertEqual('dd.d', self.configfile.getVariable('DDD'))

    def test_getVariable_empty(self):
        self.assertEqual('', self.configfile.getVariable('AAA'))
        self.assertEqual('', self.configfile.getVariable('BBB'))

    def test_getVariable_nonexistent(self):
        self.assertIs(None, self.configfile.getVariable('FFF'))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


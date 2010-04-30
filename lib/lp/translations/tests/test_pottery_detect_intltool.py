# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os
import tarfile
import unittest

from StringIO import StringIO
from textwrap import dedent

from bzrlib.bzrdir import BzrDir
from canonical.launchpad.scripts.tests import run_script
from lp.translations.pottery.detect_intltool import is_intltool_structure
from canonical.buildd.pottery.intltool import (
    ConfigFile, check_potfiles_in, find_intltool_dirs, find_potfiles_in,
    generate_pot, generate_pots, get_translation_domain)
from lp.testing import TestCase


class SetupTestPackageMixin(object):

    test_data_dir = "pottery_test_data"

    def prepare_package(self, packagename):
        """Unpack the specified package in a temporary directory.

        Change into the package's directory.
        """
        # First build the path for the package.
        packagepath = os.path.join(
            os.getcwd(), os.path.dirname(__file__),
            self.test_data_dir, packagename + ".tar.bz2")
        # Then change into the temporary directory and unpack it.
        self.useTempDir()
        tar = tarfile.open(packagepath, "r:bz2")
        tar.extractall()
        tar.close()
        os.chdir(packagename)


class TestDetectIntltool(TestCase, SetupTestPackageMixin):

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


class TestGenerateTemplates(TestCase, SetupTestPackageMixin):

    def test_generate_pot(self):
        # Generate a given PO template.
        self.prepare_package("intltool_full_ok")
        self.assertTrue(
            generate_pot("./po-module1", "module1"),
            "PO template generation failed.")
        expected_path = "./po-module1/module1.pot"
        self.assertTrue(
            os.access(expected_path, os.F_OK),
            "Generated PO template '%s' not found." % expected_path)

    def test_generate_pot_no_domain(self):
        # Generate a generic PO template.
        self.prepare_package("intltool_full_ok")
        self.assertTrue(
            generate_pot("./po-module1", None),
            "PO template generation failed.")
        expected_path = "./po-module1/messages.pot"
        self.assertTrue(
            os.access(expected_path, os.F_OK),
            "Generated PO template '%s' not found." % expected_path)

    def test_generate_pot_empty_domain(self):
        # Generate a generic PO template.
        self.prepare_package("intltool_full_ok")
        self.assertTrue(
            generate_pot("./po-module1", ""),
            "PO template generation failed.")
        expected_path = "./po-module1/messages.pot"
        self.assertTrue(
            os.access(expected_path, os.F_OK),
            "Generated PO template '%s' not found." % expected_path)

    def test_generate_pot_not_intltool(self):
        # Fail when not an intltool setup.
        self.prepare_package("intltool_full_ok")
        # Cripple the setup.
        os.remove("./po-module1/POTFILES.in")
        self.assertFalse(
            generate_pot("./po-module1", "nothing"),
            "PO template generation should have failed.")
        not_expected_path = "./po-module1/nothing.pot"
        self.assertFalse(
            os.access(not_expected_path, os.F_OK),
            "Not expected PO template '%s' generated." % not_expected_path)

    def test_generate_pots(self):
        # Generate all PO templates in the package.
        self.prepare_package("intltool_full_ok")
        expected_paths = [
            './po-module1/packagename-module1.pot',
            './po-module2/packagename-module2.pot',
            ]
        pots_list = generate_pots()
        self.assertEqual(expected_paths, pots_list)
        for expected_path in expected_paths:
            self.assertTrue(
                os.access(expected_path, os.F_OK),
                "Generated PO template '%s' not found." % expected_path)

    def test_pottery_generate_intltool_script(self):
        # Let the script run to see it works fine.
        self.prepare_package("intltool_full_ok")

        return_code, stdout, stderr = run_script(
            'scripts/rosetta/pottery-generate-intltool.py', [])

        self.assertEqual(dedent("""\
            ./po-module1/packagename-module1.pot
            ./po-module2/packagename-module2.pot
            """), stdout)


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


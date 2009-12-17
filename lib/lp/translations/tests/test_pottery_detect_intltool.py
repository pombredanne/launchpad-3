# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import os
import os.path
import shutil
import tarfile
import tempfile
import unittest

from StringIO import StringIO
from textwrap import dedent

from lp.translations.pottery import detect_intltool
from lp.testing import TestCase

class TestDetectIntltool(TestCase):

    def setUp(self):
        super(TestDetectIntltool, self).setUp()
        # Determine test directoy and create temporary working directory.
        self.curdir = os.getcwd()
        self.testdir = os.path.join(self.curdir, os.path.dirname(__file__))
        self.workdir = tempfile.mkdtemp()
        os.chdir(self.workdir)

    def tearDown(self):
        # Remove temporary directory.
        os.chdir(self.curdir)
        shutil.rmtree(self.workdir)

    def _prepare_package(self, packagename):
        # Unpack the specified pacakge to run the test against it.
        # Change to this directory.
        packagepath = os.path.join(self.testdir, packagename+".tar.bz2")
        tar = tarfile.open(packagepath, "r:bz2")
        tar.extractall()
        tar.close()
        os.chdir(packagename)

    def test_detect_potfiles_in(self):
        # Find POTFILES.in in a packge with multiple dirs,
        # only one has POTFILES.in.
        self._prepare_package("intltool_POTFILES_in_1")
        dirs = detect_intltool.find_potfiles_in()
        self.assertContentEqual(["./po-intltool"], dirs)

    def test_detect_potfiles_in_module(self):
        # Find POTFILES.in in a packge with POTFILES.in at different levels.
        self._prepare_package("intltool_POTFILES_in_2")
        dirs = detect_intltool.find_potfiles_in()
        self.assertContentEqual(["./po", "./module1/po"], dirs)

    def test_check_potfiles_in_content_ok(self):
        # Ideally all files listed in POTFILES.in exist in the source package.
        self._prepare_package("intltool_single_ok")
        self.assertTrue(detect_intltool.check_potfiles_in("./po")) 

    def test_check_potfiles_in_content_ok_file_added(self):
        # If a file is not listed in POTFILES.in, the file is still good for
        # our purposes.
        self._prepare_package("intltool_single_ok")
        added_file = file("./src/sourcefile_new.c", "w")
        added_file.write("/* Test file. */")
        added_file.close()
        self.assertTrue(detect_intltool.check_potfiles_in("./po")) 

    def test_check_potfiles_in_content_not_ok_file_removed(self):
        # If a file is missing that is listed in POTFILES.in, the file
        # intltool structure is probably broken and cannot be used for
        # our purposes.
        self._prepare_package("intltool_single_ok")
        os.remove("./src/sourcefile1.c")
        self.assertFalse(detect_intltool.check_potfiles_in("./po")) 

    def test_check_potfiles_in_wrong_directory(self):
        # Passing in the wrong directory will cause the check to fail
        # gracefully and return False.
        self._prepare_package("intltool_single_ok")
        self.assertFalse(detect_intltool.check_potfiles_in("./foo")) 

    def test_find_intltool_dirs(self):
        # Complete run: find all directories with intltool structure.
        self._prepare_package("intltool_full_ok")
        self.assertContentEqual(
            ["./po-module1", "./po-module2"],
            detect_intltool.find_intltool_dirs())

    def test_find_intltool_dirs_broken(self):
        # Complete run: part of the intltool structure is broken.
        self._prepare_package("intltool_full_ok")
        os.remove("./src/module1/sourcefile1.c")
        self.assertContentEqual(
            ["./po-module2"],
            detect_intltool.find_intltool_dirs())


class TestConfigFile(TestCase):

    def setUp(self):
        self.configfile = ConfigFile(StringIO(dedent("""\
            # Demo config file
            AAA=
            BBB = 
            CCC = ccc 
            DDD=ddd
            """)))

    def test_getVariable_exists(self):
        self.assertEqual('ccc', configfile.getVariable('CCC'))
        self.assertEqual('ddd', configfile.getVariable('DDD'))

    def test_getVariable_empty(self):
        self.assertEqual('', configfile.getVariable('AAA'))
        self.assertEqual('', configfile.getVariable('BBB'))

    def test_getVariable_nonexistent(self):
        self.assertIs(None, configfile.getVariable('FFF'))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


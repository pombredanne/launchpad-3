#!/usr/bin/env python

# Copyright (C) 2004  James Troup <james.troup@canonical.com>

import os, sys, unittest

from canonical.lucille.tests import datadir

datatoplevel = datadir("")

class TestCheckUpload(unittest.TestCase):

    def Dict(self, **dict):
        return dict

    def sort_reject(self, s):
        """Sort the a reject message."""
        x = s.split('\n')[:-1]
        x.sort()
        return '\n'.join(x)+'\n'

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testImport(self):
        """Can check_upload.check_upload be imported"""
        from canonical.lucille.checks import UploadCheck

    def testInstatiate(self):
        """Can checks.UploadCheck be instantiated"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()
        self.failUnless(isinstance(u, UploadCheck))
        self.assertEqual(u.reject_message, "")
        self.assertEqual(u.changes_filename, "")

    # reject()
    def testReject(self):
        """Test reject()"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()
        u.reject("test")
        self.assertEqual(u.reject_message, "REJECTED: test\n")

    def testRejectWithPrefix(self):
        """Test reject() with a prefix argument"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()
        u.reject("test", "ACCEPTED: ")
        self.assertEqual(u.reject_message, "ACCEPTED: test\n")

    def testRejectEmptyArgument(self):
        """Test reject() with an empty string"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()
        u.reject("")
        self.assertEqual(u.reject_message, "")

    def testStrIsNum(self):
        """Test str_isnum() with various input"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()
        self.assertEqual(u.str_isnum("0"), 1)
        self.assertEqual(u.str_isnum("2356"), 1)
        self.assertEqual(u.str_isnum("23a"), 0)
        self.assertEqual(u.str_isnum("a23"), 0)
        self.assertEqual(u.str_isnum("2a3"), 0)
        self.assertEqual(u.str_isnum(""), 0)

    # changes_val_mandatory()
    def testChangesValMandatory(self):
        """Test changes_val_mandatory() with no missing fields"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()
        u.changes = self.Dict(source="", binary="", architecture="", version="",
                              distribution="", maintainer="", files="", changes="")
        u.changes_val_mandatory()
        self.assertEqual(u.reject_message, "")

    def testChangesValMandatoryBroken(self):
        """Test changes_mandatory() with all missing fields"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()
        u.changes = {}
        u.changes_val_mandatory()
        expected = """REJECTED: : missing mandatory field 'Architecture'
REJECTED: : missing mandatory field 'Binary'
REJECTED: : missing mandatory field 'Changes'
REJECTED: : missing mandatory field 'Distribution'
REJECTED: : missing mandatory field 'Files'
REJECTED: : missing mandatory field 'Maintainer'
REJECTED: : missing mandatory field 'Source'
REJECTED: : missing mandatory field 'Version'
"""
        received = self.sort_reject(u.reject_message)
        self.assertEqual(received, expected)

    ########################################

    # changes_val_closes()
    def testChangesValCloses(self):
        """Test changes_val_closes() with valid 'Closes'"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()

        u.changes = self.Dict(closes="203410 198732")
        u.changes_val_closes()
        self.assertEqual(u.reject_message, "")

        u.changes["closes"]="203410"
        u.changes_val_closes()
        self.assertEqual(u.reject_message, "")

        u.changes["closes"]=""
        u.changes_val_closes()
        self.assertEqual(u.reject_message, "")

    def testChangesValClosesInvalid(self):
        """Test changes_val_closes() with invalid 'Closes'"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()

        u.changes = self.Dict(closes="203410a 198732")
        u.changes_val_closes()
        self.assertEqual(u.reject_message,
                         "REJECTED: : '203410a' in 'Closes' field isn't a number\n")

        u.reject_message = ""
        u.changes["closes"]="iamnotanumber"
        u.changes_val_closes()
        self.assertEqual(u.reject_message,
                         "REJECTED: : 'iamnotanumber' in 'Closes' field isn't a number\n")

        u.reject_message = ""
        u.changes["closes"]="a free man"
        u.changes_val_closes()
        expected = """REJECTED: : 'a' in 'Closes' field isn't a number
REJECTED: : 'free' in 'Closes' field isn't a number
REJECTED: : 'man' in 'Closes' field isn't a number
"""
        received = self.sort_reject(u.reject_message)
        self.assertEqual(received, expected)

    ########################################

    # changes_val_files()
    def testChangesValFiles(self):
        """Test changes_val_files()"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()

        u.changes = self.Dict(files="something")
        u.changes_val_files()
        self.assertEqual(u.reject_message, "")
        u.changes["files"] = ""
        u.changes_val_files()
        self.assertEqual(u.reject_message, "REJECTED: : 'Files' field is empty\n")

    ########################################

    # val_sig()
    def testValSig(self):
        """Test val_sig()"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()

        u.directory = datatoplevel
        u.keyring = os.path.join(u.directory, "pubring.gpg")
        u.changes_filename = "good-signed-changes"
        u.val_sig(u.changes_filename)

        u.changes_filename = "bad-signed-changes"
        u.val_sig(u.changes_filename)
        expected = "REJECTED: %s: bad signature\n" % (u.absname(u.changes_filename))
        self.assertEqual(u.reject_message, expected)

    ########################################

    # changes_parse()
    def testChangesParse(self):
        """Test changes_parse()"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()

        u.directory = datatoplevel
        u.changes_filename = "good-signed-changes"
        u.changes_parse()

        u.changes_filename = "empty-file"
        u.changes_parse()
        expected = "REJECTED: %s: empty file\n" % u.absname(u.changes_filename)
        self.assertEqual(u.reject_message, expected)

    ########################################

    # files_build()
    def testFilesBuild(self):
        """Test files_build()"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()

        u.directory = datatoplevel
        u.changes_filename = "good-signed-changes"
        u.changes_parse()
        u.files = u.files_build(u.changes)

        del u.changes["files"]
        u.files = u.files_build(u.changes)
        # ??? bad exception message in TagFiles.build_file_list()
        expected = "REJECTED: No Files section in supplied tagfile\n"
        self.assertEqual(u.reject_message, expected)

    ########################################
    
    # val_email()
    def testValEmail(self):
        """Test val_email()"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()

        u.directory = datatoplevel
        u.changes_filename = "good-signed-changes"
        u.changes_parse()
        u.val_email(u.changes["maintainer"], "Maintainer", u.changes_filename)

        u.changes["maintainer"] = "James Troup <james@nocrew.org"
        u.val_email(u.changes["maintainer"], "Maintainer", u.changes_filename)
        expected = "REJECTED: %s: %s: doesn't parse as a valid Maintainer field.\n" % (u.changes_filename, u.changes["maintainer"])
        self.assertEqual(u.reject_message, expected)

    ########################################

    # changes_val_source_exists()
    def testChangesValSourceExists(self):
        """Test changes_val_source_exists()"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()

        u.directory = datatoplevel
        u.changes_filename = "good-signed-changes"
        u.changes_parse()
        u.changes_val_source_exists()

        u.changes_filename = "binutils_2.15-4_i386.changes"
        u.changes_parse()
        u.files = u.files_build(u.changes)
        u.changes_val_source_exists()

        for filename in u.files:
            if filename.endswith(".dsc"):
                to_delete = filename
        del u.files[to_delete]
        u.changes_val_source_exists()
        expected = "REJECTED: %s: no source found and 'Architecture' contains 'source'\n" % (u.changes_filename)
        self.assertEqual(u.reject_message, expected)

    ########################################

    # files_val_source()
    def testFilesValSource(self):
        """Test files_val_source()"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()
        u.directory = datatoplevel
        u.changes_filename = "good-signed-changes"
        u.changes_parse()
        u.files = u.files_build(u.changes)
        u.files_val_source()
        self.assertEqual(u.reject_message, "")

        u.changes_filename = "binutils_2.15-4_i386.changes"
        u.changes_parse()
        u.files = u.files_build(u.changes)
        u.files_val_source()
        self.assertEqual(u.reject_message, "")

        for filename in u.files:
            if filename.endswith(".diff.gz"):
                to_delete = filename
        del u.files[to_delete]
        u.files_val_source()
        expected = "REJECTED: %s: .dsc but no .diff.gz\n" % (u.changes_filename)
        self.assertEqual(u.reject_message, expected)

        u.reject_message = ""
        u.files[to_delete] = {}
        u.files["moo.dsc"] = {}
        u.files["moo.diff.gz"] = {}
        u.files["moo.tar.gz"] = {}
        u.files["moo.orig.tar.gz"] = {}
        u.files_val_source()
        expected = """REJECTED: %s: only one source package per .changes (> 1 .diff.gz found)
REJECTED: %s: only one source package per .changes (> 1 .dsc found)
REJECTED: %s: only one source package per .changes (> 1 .tar.gz found)
""" % (u.changes_filename, u.changes_filename, u.changes_filename)
        received = self.sort_reject(u.reject_message)
        self.assertEqual(received, expected)

    ########################################

    # dsc_get_filename()
    def testDscGetFilename(self):
        """Test dsc_get_filename()"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()

        u.directory = datatoplevel
        u.changes_filename = "binutils_2.15-4_i386.changes"
        u.changes_parse()
        u.files = u.files_build(u.changes)
        u.dsc_get_filename()
        self.assertEqual(u.dsc_filename, "binutils_2.15-4.dsc")

        del u.files[u.dsc_filename]
        u.dsc_filename = ""
        u.dsc_get_filename()
        self.assertEqual(u.dsc_filename, "")

    # dsc_parse()
    def testDscParse(self):
        """Test dsc_parse()"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()

        u.directory = datatoplevel
        u.dsc_filename = "binutils_2.15-4.dsc"
        u.dsc_parse()
        self.assertEqual(u.reject_message, "")

        u.dsc_filename = "empty-file"
        u.dsc_parse()
        expected = "REJECTED: %s: empty file\n" % u.absname(u.dsc_filename)
        self.assertEqual(u.reject_message, expected)

    ########################################

    # dsc_val_mandatory()
    def testDscValMandatory(self):
        """Test dsc_val_mandatory() with no missing fields"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()
        u.directory = datatoplevel
        u.dsc_filename = "binutils_2.15-4.dsc"
        u.dsc_parse()
        u.dsc_val_mandatory()
        self.assertEqual(u.reject_message, "")

    def testDscValMandatoryBroken(self):
        """Test dsc_mandatory() with all missing fields"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()
        u.dsc = {}
        u.dsc_filename = ""
        u.dsc_val_mandatory()
        expected = """REJECTED: : missing mandatory field 'Architecture'
REJECTED: : missing mandatory field 'Binary'
REJECTED: : missing mandatory field 'Files'
REJECTED: : missing mandatory field 'Format'
REJECTED: : missing mandatory field 'Maintainer'
REJECTED: : missing mandatory field 'Source'
REJECTED: : missing mandatory field 'Version'
"""
        received = self.sort_reject(u.reject_message)
        self.assertEqual(received, expected)

    ########################################
    
    # dsc_val_source()
    # "^[\dA-Za-z][\dA-Za-z\+\-\.]+$"
    def testDscValSource(self):
        """Test dsc_val_source()"""
        from canonical.lucille.checks import UploadCheck

        u = UploadCheck()
        u.directory = datatoplevel
        u.dsc_filename = "binutils_2.15-4.dsc"
        u.dsc_parse()
        u.dsc_val_source()
        self.assertEqual(u.reject_message, "")

        # Valid
        for source in [ "libstdc++", "3270", "hi", "BINUTILS", "bin-utils", "bin.utils" ]:
            u.dsc["source"] = source
            u.dsc_val_source()
            self.assertEqual(u.reject_message, "")

        # Invalid
        for source in [ "binutils!", "+binutils", "bin_utils", "a", "" ]:
            u.reject_message = ""
            u.dsc["source"] = source
            u.dsc_val_source()
            self.assertEqual(u.reject_message, "REJECTED: %s: invalid source name '%s'\n" \
                             % (u.dsc_filename, source))

    ########################################

    # dsc_val_version()
    # "^([0-9]+:)?[0-9A-Za-z\.\-\+:]+$"
    def testDscValVersion(self):
        """Test dsc_val_version()"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()
        u.directory = datatoplevel
        u.dsc_filename = "binutils_2.15-4.dsc"
        u.dsc_parse()
        u.dsc_val_version()
        self.assertEqual(u.reject_message, "")

        # Valid
        for version in [ "3:2.15-4", "6", "6-release+6.6" ]:
            u.dsc["version"] = version
            u.dsc_val_version()
            self.assertEqual(u.reject_message, "")

        # Invalid
        for version in [ "2!", "2.15_4", "" ]:
            u.reject_message = ""
            u.dsc["version"] = version
            u.dsc_val_version()
            self.assertEqual(u.reject_message, "REJECTED: %s: invalid version number '%s'\n" \
                             % (u.dsc_filename, version))


    ########################################

    # dsc_val_format()
    def testDscValFormat(self):
        """Test dsc_val_format()"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()
        u.directory = datatoplevel
        u.dsc_filename = "binutils_2.15-4.dsc"
        u.dsc_parse()
        u.dsc_val_format()
        self.assertEqual(u.reject_message, "")

        u.dsc["format"] = "1.1"
        u.dsc_val_format()
        self.assertEqual(u.reject_message, "REJECTED: %s: incompatible source package format '%s' in 'Format' field\n" \
                         % (u.dsc_filename, u.dsc["format"]))

    ########################################

    # dsc_val_build_dep()
    def testDscValBuildDep(self):
        """Test dsc_val_build_dep()"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()
        u.directory = datatoplevel
        u.dsc_filename = "binutils_2.15-4.dsc"
        u.dsc_parse()
        u.dsc_val_build_dep("build-depends")
        self.assertEqual(u.reject_message, "")
        u.dsc_val_build_dep("build-depends-indep")
        self.assertEqual(u.reject_message, "")

        # Valid
        valid = [ "bc (>= 2.3) [hurd-i386 powerpc], dc", "binARRAYutils",
                  "bc (<< 3.4) [!s390 !mips], dc" ]
        for build_dep in valid:
            u.dsc["build-depends"] = build_dep
            u.dsc_val_build_dep("build-depends")
            self.assertEqual(u.reject_message, "")

        # Invalid
        invalid = [ "bc dc", "bc [powerpc] (>= 2.3)" ]
        for build_dep in invalid:
            u.reject_message = ""
            u.dsc["build-depends"] = build_dep
            u.dsc_val_build_dep("build-depends")
            expected = "REJECTED: %s: invalid 'Build-Depends' field can not be parsed by apt\n" \
                       % (u.dsc_filename)
            self.assertEqual(u.reject_message, expected)

        u.reject_message = ""
        u.dsc["build-depends"] = "ARRAY"
        u.dsc_val_build_dep("build-depends")
        expected = "REJECTED: %s: invalid 'Build-Depends' field produced by broken dpkg-dev\n" \
                   % (u.dsc_filename)
        self.assertEqual(u.reject_message, expected)
        
    ########################################

    # dsc_version_against_changes()
    def testDscVersionAgainstChanges(self):
        """Test dsc_version_against_changes()"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()
        u.directory = datatoplevel
        u.changes_filename = "binutils_2.15-4_i386.changes"
        u.changes_parse()
        u.files = u.files_build(u.changes)
        u.dsc_filename = "binutils_2.15-4.dsc"
        u.dsc_parse()
        u.dsc_version_against_changes()
        self.assertEqual(u.reject_message, "")

    ########################################

    # dsc_val_files
    def testDscValFiles(self):
        """Test dsc_val_files()"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()
        u.directory = datatoplevel
        u.dsc_filename = "binutils_2.15-4.dsc"
        u.dsc_parse()
        u.dsc_files = u.files_build(u.dsc, is_dsc=True)
        u.dsc_val_files()
        self.assertEqual(u.reject_message, "")

        u.dsc_files["moo.deb"] = {}
        u.dsc_val_files()
        expected = "REJECTED: %s: unrecognised file 'moo.deb' in 'Files' field\n" \
                   % (u.dsc_filename)
        self.assertEqual(u.reject_message, expected)
        del u.dsc_files["moo.deb"]
        u.reject_message = ""

        u.dsc_files["moo.diff.gz"] = {}
        u.dsc_files["moo.tar.gz"] = {} 
        u.dsc_val_files()
        expected = """REJECTED: %s: more than one .diff.gz in 'Files' field
REJECTED: %s: more than one .tar.gz in 'Files' field
""" % (u.dsc_filename, u.dsc_filename)
        received = self.sort_reject(u.reject_message)
        self.assertEqual(received, expected)
        u.reject_message = ""

        u.dsc_files.clear()
        u.dsc_val_files()
        expected = """REJECTED: %s: no .diff.gz in 'Files' field
REJECTED: %s: no .tar.gz or .orig.tar.gz in 'Files' field
""" % (u.dsc_filename, u.dsc_filename)
        received = self.sort_reject(u.reject_message)
        self.assertEqual(received, expected)
        u.reject_message = ""

    ########################################

    # check_source_package()
    def testCheckSourcePackage(self):
        """Test check_source_package()"""
        from canonical.lucille.checks import UploadCheck
        u = UploadCheck()
        u.directory = datatoplevel
        u.dsc_filename = "ed_0.2-20.dsc"
        u.check_source_package()
        self.assertEqual(u.reject_message, "")

################################################################################

def test_suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestCheckUpload))
    return suite

def main(argv):
    suite = test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    if not runner.run(suite).wasSuccessful():
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))


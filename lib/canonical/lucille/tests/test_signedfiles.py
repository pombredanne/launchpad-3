#!/usr/bin/env python

# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: f815ad2f-cd34-4399-81a1-c226a949e6b5

import unittest
import sys
import os
import shutil
from canonical.lucille.tests import datadir


class TestSignedFiles(unittest.TestCase):

    def testImport(self):
        """canonical.lucille.GPGV should be importable"""
        from canonical.lucille.GPGV import verify_signed_file

    def testCheckGoodSignedChanges(self):
        """canonical.lucille.GPGV.verify_signed_file should cope with a good
           changes file
        """
        from canonical.lucille.GPGV import verify_signed_file
        s = verify_signed_file(datadir("good-signed-changes"),
                               [datadir("pubring.gpg")])
        self.assertEquals(s, "B94E5B41DAA4B3CD521BEBA03AD3DF3EF2D2C028")

    def testCheckBadSignedChangesRaises1(self):
        """canonical.lucille.GPGV.verify_signed_file should raise
           TaintedFileNameError
        """
        from canonical.lucille.GPGV import verify_signed_file
        from canonical.lucille.GPGV import TaintedFileNameError
        self.assertRaises(TaintedFileNameError, verify_signed_file, "*", [])
        self.assertRaises(TaintedFileNameError,
                          verify_signed_file, "foo", [], "*" )

    def testCheckExpiredSignedChanges(self):
        """canonical.lucille.GPGV.verify_signed_file should raise
           SignatureExpiredError
        """
        from canonical.lucille.GPGV import verify_signed_file
        from canonical.lucille.GPGV import SignatureExpiredError
        self.assertRaises(SignatureExpiredError,
                          verify_signed_file,
                          datadir("expired-signed-changes"),
                          [datadir("pubring.gpg")])

    def testCheckRevokedSignedChanges(self):
        """canonical.lucille.GPGV.verify_signed_file should raise
           KeyRevokedError
        """
        from canonical.lucille.GPGV import verify_signed_file, KeyRevokedError
        self.assertRaises(KeyRevokedError,
                          verify_signed_file,
                          datadir("revoked-signed-changes"),
                          [datadir("pubring.gpg")])

    def testCheckBadSignedChanges(self):
        """canonical.lucille.GPGV.verify_signed_file should raise
           BadSignatureError
        """
        from canonical.lucille.GPGV import verify_signed_file
        from canonical.lucille.GPGV import BadSignatureError
        self.assertRaises(BadSignatureError,
                          verify_signed_file,
                          datadir("bad-signed-changes"),
                          [datadir("pubring.gpg")])

    def testCheckNotSignedChanges(self):
        """canonical.lucille.GPGV.verify_signed_file should raise
           NoSignatureFoundError
        """
        from canonical.lucille.GPGV import verify_signed_file
        from canonical.lucille.GPGV import NoSignatureFoundError
        self.assertRaises(NoSignatureFoundError,
                          verify_signed_file,
                          datadir("singular-stanza"),
                          [datadir("pubring.gpg")])

    def testCheckPubkeyNotFound(self):
        """canonical.lucille.GPGV.verify_signed_file should raise
           NoPublicKeyError
        """
        from canonical.lucille.GPGV import verify_signed_file
        from canonical.lucille.GPGV import NoPublicKeyError
        self.assertRaises(NoPublicKeyError,
                          verify_signed_file,
                          datadir("good-signed-changes"),
                          [datadir("empty-file")])

    def testCheckPubkeyNotFoundDetailsKey(self):
        """canonical.lucille.GPGV.verify_signed_file should raise
           NoPublicKeyError with the right key id
        """
        from canonical.lucille.GPGV import verify_signed_file
        from canonical.lucille.GPGV import NoPublicKeyError
        try:
            verify_signed_file(datadir("good-signed-changes"),
                               [datadir("empty-file")])
        except NoPublicKeyError, err:
            self.assertEquals(err.key, '3AD3DF3EF2D2C028')

def test_suite():
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestSignedFiles))
    return suite

def main(argv):
    suite = test_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    if not runner.run(suite).wasSuccessful():
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))


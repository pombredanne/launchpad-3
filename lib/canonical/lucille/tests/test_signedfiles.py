#!/usr/bin/env python

# arch-tag: f815ad2f-cd34-4399-81a1-c226a949e6b5

import unittest
import sys
import shutil

class TestSignedFiles(unittest.TestCase):
    def testImport(self):
        """canonical.lucille.GPGV should be importable"""
        from canonical.lucille.GPGV import verify_signed_file

    def testCheckGoodSignedChanges(self):
        """canonical.lucille.GPGV.verify_signed_file should cope with a good changes file"""
        from canonical.lucille.GPGV import verify_signed_file
        s = verify_signed_file( "data/good-signed-changes", ["data/pubring.gpg"] )
        self.assertEquals( s, "B94E5B41DAA4B3CD521BEBA03AD3DF3EF2D2C028" )

    def testCheckBadSignedChangesRaises1(self):
        """canonical.lucille.GPGV.verify_signed_file should raise TaintedFileNameError"""
        from canonical.lucille.GPGV import verify_signed_file, TaintedFileNameError
        self.assertRaises( TaintedFileNameError, verify_signed_file, "*", [] )
        self.assertRaises( TaintedFileNameError, verify_signed_file, "foo", [], "*" )
        pass

    def testCheckExpiredSignedChanges(self):
        """canonical.lucille.GPGV.verify_signed_file should raise SignatureExpiredError"""
        from canonical.lucille.GPGV import verify_signed_file, SignatureExpiredError
        self.assertRaises( SignatureExpiredError,
                           verify_signed_file,
                           "data/expired-signed-changes",
                           [ "data/pubring.gpg" ] )

    def testCheckRevokedSignedChanges(self):
        """canonical.lucille.GPGV.verify_signed_file should raise KeyRevokedError"""
        from canonical.lucille.GPGV import verify_signed_file, KeyRevokedError
        self.assertRaises( KeyRevokedError,
                           verify_signed_file,
                           "data/revoked-signed-changes",
                           [ "data/pubring.gpg" ] )
        
    def testCheckBadSignedChanges(self):
        """canonical.lucille.GPGV.verify_signed_file should raise BadSignatureError"""
        from canonical.lucille.GPGV import verify_signed_file, BadSignatureError
        self.assertRaises( BadSignatureError,
                           verify_signed_file,
                           "data/bad-signed-changes",
                           [ "data/pubring.gpg" ] )
        
    def testCheckNotSignedChanges(self):
        """canonical.lucille.GPGV.verify_signed_file should raise NoSignatureFoundError"""
        from canonical.lucille.GPGV import verify_signed_file, NoSignatureFoundError
        self.assertRaises( NoSignatureFoundError,
                           verify_signed_file,
                           "data/singular-stanza",
                           [ "data/pubring.gpg" ] )
        
def main(argv):
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(TestSignedFiles))
    runner = unittest.TextTestRunner(verbosity = 2)
    if not runner.run(suite).wasSuccessful():
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))


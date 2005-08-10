# Copyright 2005 Canonical Ltd.  All rights reserved.

import unittest
import canonical.base

class TestKeyRingAnalyser(unittest.TestCase):
    def testImports(self):
        """Can the KeyRing module be imported"""
        from canonical.launchpad.utilities.keyring_trust_analyser import (
            KeyRingTrustAnalyser)

def test_suite():
    loader=unittest.TestLoader()
    result = loader.loadTestsFromName(__name__)
    return result

if __name__ == "__main__":
    unittest.main(defaultTest=test_suite())



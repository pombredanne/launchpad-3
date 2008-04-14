# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest
import sha
import binascii
from zope.component import getUtility
from zope.app.testing import ztapi
from zope.app.testing.placelesssetup import PlacelessSetup
from canonical.launchpad.webapp.authentication import SSHADigestEncryptor
from canonical.launchpad.interfaces import IPasswordEncryptor

class TestSSHADigestEncryptor(PlacelessSetup, unittest.TestCase):

    def setUp(self):
        PlacelessSetup.setUp(self)
        encryptor = SSHADigestEncryptor()
        ztapi.provideUtility(IPasswordEncryptor, encryptor)

    def test_encrypt(self):
        encryptor = getUtility(IPasswordEncryptor)
        encrypted1 = encryptor.encrypt('motorhead')
        encrypted2 = encryptor.encrypt('motorhead')
        self.failIfEqual(encrypted1, encrypted2)
        salt = encrypted1[20:]
        v = binascii.b2a_base64(
            sha.new('motorhead' + salt).digest() + salt
            )[:-1]
        return (v == encrypted1)

    def test_validate(self):
        encryptor = getUtility(IPasswordEncryptor)
        self.assertEqual(encryptor.validate(
            'motorhead', '+uSsxIfQDRUxG1oDTu1SsQN0P0RTl4SL9XRd'), True)

    def test_unicode_encrypt(self):
        encryptor = getUtility(IPasswordEncryptor)
        encrypted1 = encryptor.encrypt(u'motorhead')
        encrypted2 = encryptor.encrypt(u'motorhead')
        self.failIfEqual(encrypted1, encrypted2)
        salt = encrypted1[20:]
        v = binascii.b2a_base64(sha.new('motorhead' + salt).digest() + salt)[:-1]
        return (v == encrypted1)

    def test_unicode_validate(self):
        encryptor = getUtility(IPasswordEncryptor)
        self.assertEqual(encryptor.validate(
            u'motorhead', u'+uSsxIfQDRUxG1oDTu1SsQN0P0RTl4SL9XRd'), True)

    def test_nonunicode_password(self):
        encryptor = getUtility(IPasswordEncryptor)
        try:
            encryptor.encrypt(u'motorhead\xc3\xb3')
        except UnicodeEncodeError:
            pass
        else:
            self.fail("uncaught non-ascii text")


def test_suite():
    t = unittest.makeSuite(TestSSHADigestEncryptor)
    return unittest.TestSuite((t,))

if __name__=='__main__':
    main(defaultTest='test_suite')

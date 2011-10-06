# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


import binascii
import hashlib
import unittest

from zope.app.testing import ztapi
from zope.app.testing.placelesssetup import PlacelessSetup
from zope.component import getUtility

from canonical.launchpad.interfaces.launchpad import IPasswordEncryptor
from canonical.launchpad.webapp.authentication import SSHADigestEncryptor


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
            hashlib.sha1('motorhead' + salt).digest() + salt)[:-1]
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
        v = binascii.b2a_base64(
            hashlib.sha1('motorhead' + salt).digest() + salt)[:-1]
        return v == encrypted1

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

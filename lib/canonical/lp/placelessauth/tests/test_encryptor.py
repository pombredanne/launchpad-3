import unittest
from zope.app.tests.placelesssetup import PlacelessSetup
from canonical.lp.placelessauth.encryption import SSHADigestEncryptor
from canonical.lp.placelessauth.interfaces import IPasswordEncryptor
from zope.app.tests import ztapi
from zope.app import zapi
from binascii import b2a_base64
import sha

class TestSSHADigestEncryptor(PlacelessSetup, unittest.TestCase):

    def setUp(self):
        PlacelessSetup.setUp(self)
        encryptor = SSHADigestEncryptor()
        ztapi.provideUtility(IPasswordEncryptor, encryptor)

    def test_encrypt(self):
        encryptor = zapi.getUtility(IPasswordEncryptor)
        encrypted1 = encryptor.encrypt('motorhead')
        encrypted2 = encryptor.encrypt('motorhead')
        self.failIfEqual(encrypted1, encrypted2)
        salt = encrypted1[20:]
        v = b2a_base64(sha.new('motorhead' + salt).digest() + salt)[:-1]
        return (v == encrypted1)

    def test_validate(self):
        encryptor = zapi.getUtility(IPasswordEncryptor)
        self.assertEqual(encryptor.validate(
            'motorhead', '+uSsxIfQDRUxG1oDTu1SsQN0P0RTl4SL9XRd'), True)

def test_suite():
    t = unittest.makeSuite(TestSSHADigestEncryptor)
    return unittest.TestSuite((t,))

if __name__=='__main__':
    main(defaultTest='test_suite')

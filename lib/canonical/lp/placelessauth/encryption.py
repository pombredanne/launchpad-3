from canonical.lp.placelessauth.interfaces import IPasswordEncryptor
from zope.interface import implements
import binascii
import random
import sha

class SSHADigestEncryptor(object):
    '''
    SSHA is a modification of the SHA digest scheme with a salt
    starting at byte 20 of the base64-encoded string.
    '''
    implements(IPasswordEncryptor)

    # Source: http://developer.netscape.com/docs/technote/ldap/pass_sha.html

    saltLength = 20
    
    def generate_salt(self):
        # Salt can be any length, but not more than about 37 characters
        # because of limitations of the binascii module.
        # All 256 characters are available.
        salt = ''
        for n in range(self.saltLength):
            salt += chr(random.randrange(256))
        return salt

    def encrypt(self, plaintext, salt=None):
        plaintext = str(plaintext)
        if salt is None:
            salt = self.generate_salt()
        v = binascii.b2a_base64(sha.new(plaintext + salt).digest() + salt)
        return v[:-1]

    def validate(self, plaintext, encrypted):
        encrypted = str(encrypted)
        plaintext = str(plaintext)
        try:
            ref = binascii.a2b_base64(encrypted)
        except binascii.Error:
            # Not valid base64.
            return 0
        salt = ref[20:]
        v = binascii.b2a_base64(sha.new(plaintext + salt).digest() + salt)[:-1]
        return (v == encrypted)

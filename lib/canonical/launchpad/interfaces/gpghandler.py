from zope.interface import Interface, Attribute

__all__ = ['IGPGHandler', 'IPymeSignature', 'IPymeKey', 'IPymeUserId',
           'GPGVerificationError']


class GPGVerificationError(Exception):
    """GPG verification error."""

class IGPGHandler(Interface):
    """Handler to perform GPG operations."""

    def verifySignature(content, signature=None):
        """Returns a PymeSignature object if content is correctly signed
        or None. 

        If signature is None, we assume content is clearsigned. Otherwise
        it stores the detached signature and content should contain the
        plain text in question.

        content and signature must be 8-bit encoded str objects. It's up to
        the caller to encode or decode as appropriate.

        :content: The content to be verified
        :signature: The signature (or None if content is clearsigned)
        """

    def getVerifiedSignature(content, signature=None):
        """Returns a PymeSignature object if content is correctly signed
        or else raise an exception.

        If signature is None, we assume content is clearsigned. Otherwise
        it stores the detached signature and content should contain the
        plain text in question.

        content and signature must be 8-bit encoded str objects. It's up to
        the caller to encode or decode as appropriate.

        The only exception likely to be propogated out is GPGVerificationError

        :content: The content to be verified
        :signature: The signature (or None if content is clearsigned)
        """

    def importKey(content):
        """Returns a PymeKey object refering to an just-import GPG
        public or secret key.

        content must be a traditional string. It's up to the caller to
        encode or decode properly.

        :content: public or secret key content ASCII armored
        """

    def importKeyringFile(filepath):
        """Import the keyring filepath into the local key database.

        :param filepath: the path to a keyring to import.

        :returns: a list of the imported keys.
        """

    def encryptContent(content, fingerprint):
        """Return the encrypted content or None if failed.

        content must be a traditional string. It's up to the caller to
        encode or decode properly. Fingerprint must be hexadecimal string. 

        :content: the unicode content to be encrypted.
        :fingerprint: the GPG Key's fingerprint.
        """

    def decryptContent(content, password):
        """Return the decrypted content or None if failed

        content and password must be traditional strings. It's up to
        the caller to encode or decode properly. 

        :content: encrypted data content
        :password: unicode password to unlock the secret key in question 
        """

    def retrieveKey(fingerprint):
        """Returns a PymeKey containing the just-retrieved key information
        from the local keyring, if key isn't present, import it from the
        key server before. If the process fails, it returns debug information
        about the process.

        Fingerprint must be hexadecimal string.

        :fingerprint: key fingerprint
        """

    def checkTrustDb():
        """Check whether the GPG trust database is up to date, and
        rebuild the trust values if necessary.

        The results will be visible in any new retrieved key objects.
        Existing key objects will not reflect the new trust value.
        """

    def localKeys():
        """Return an iterator of all keys locally known about by the handler.
        """

    def resetLocalState():
        """Reset the local state (i.e. GPG keyrings, trust database etc."""
        #FIXME RBC: this should be a zope test cleanup thing per SteveA.

class IPymeSignature(Interface):
    """pyME signature container."""

    fingerprint = Attribute("Signer Fingerprint.")
    plain_data = Attribute("Plain Signed Text.")


class IPymeKey(Interface):
    """pyME key model."""

    fingerprint = Attribute("Key Fingerprint")
    algorithm = Attribute("Key Algorithm")
    revoked = Attribute("Key Revoked")
    expired = Attribute("Key Expired")
    keysize = Attribute("Key Size")
    keyid = Attribute("Pseudo Key ID, composed by last fingerprint 8 digits ")
    uids = Attribute("List of user IDs associated with this key")
    emails = Attribute("List containing only well formed and non-revoked emails")
    displayname = Attribute("Key displayname: <size><type>/<keyid>")
    owner_trust = Attribute("The owner trust")

    can_encrypt = Attribute("Whether the key can be used for encrypting")
    can_sign = Attribute("Whether the key can be used for signing")
    can_certify = Attribute("Whether the key can be used for certification")
    can_authenticate = Attribute("Whether the key can be used for authentication")

    def setOwnerTrust(value):
        """Set the owner_trust value for this key."""


class IPymeUserId(Interface):
    """pyME user ID"""

    revoked = Attribute("True if the user ID has been revoked")
    invalid = Attribute("True if the user ID is invalid")
    validity = Attribute("""A measure of the validity of the user ID,
                         based on owner trust values and signatures.""")
    uid = Attribute("A string identifying this user ID")
    name = Attribute("The name portion of this user ID")
    email = Attribute("The email portion of this user ID")
    comment = Attribute("The comment portion of this user ID")

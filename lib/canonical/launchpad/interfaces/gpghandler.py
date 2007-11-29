# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

from zope.interface import Interface, Attribute

__all__ = ['IGPGHandler', 'IPymeSignature', 'IPymeKey', 'IPymeUserId',
           'GPGVerificationError', 'MoreThanOneGPGKeyFound',
           'GPGKeyNotFoundError', 'SecretGPGKeyImportDetected']


class MoreThanOneGPGKeyFound(Exception):
    """More than one GPG key was found and we don't know which one to
    import.
    """


class GPGKeyNotFoundError(Exception):
    """The given GPG key was not found in the keyserver."""


class SecretGPGKeyImportDetected(Exception):
    """An attempt to import a secret GPG key."""


class GPGVerificationError(Exception):
    """OpenPGP verification error."""


class IGPGHandler(Interface):
    """Handler to perform OpenPGP operations."""

    def sanitizeFingerprint(fingerprint):
        """Return sanitized fingerprint if well-formed, otherwise return None."""

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

    def getURLForKeyInServer(fingerprint, action=None, public=False):
        """Return the URL for that fingerprint on the configured keyserver.

        If public is True, return a URL for the public keyserver; otherwise,
        references the default (internal) keyserver.
        If action is provided, will attach that to the URL.
        """

    def getVerifiedSignatureResilient(content, signature=None):
        """Wrapper for getVerifiedSignature.

        It calls the target method exactly 3 times.

        Return the result if it succeed during the cycle, otherwise
        capture the errors and emits at the end GPGVerificationError
        with the stored error information.
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

    def importPublicKey(content):
        """Import the public key with the given content into our local keyring.

        Return a PymeKey object referring to the public key imported.

        :content: Public key ASCII armored content (must be an ASCII string;
                  it's up to the caller to encode or decode properly).

        If the secret key's ASCII armored content is given,
        SecretGPGKeyDetected is raised.

        If no key is found, GPGKeyNotFoundError is raised.  On the other
        hand, if more than one key is found, MoreThanOneGPGKeyFound is
        raised.
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

        :content: the Unicode content to be encrypted.
        :fingerprint: the OpenPGP key's fingerprint.
        """

    def retrieveKey(fingerprint):
        """Return a PymeKey object containing the key information from the
        local keyring.

        :fingerprint: The key fingerprint, which must be an hexadecimal
                      string.

        If the key with the given fingerprint is not present in the local
        keyring, first import it from the key server into the local keyring.

        If the key is not found neither in the local keyring nor in the
        key server, a GPGKeyNotFoundError is raised.
        """

    def checkTrustDb():
        """Check whether the OpenPGP trust database is up to date, and
        rebuild the trust values if necessary.

        The results will be visible in any new retrieved key objects.
        Existing key objects will not reflect the new trust value.
        """

    def localKeys():
        """Return an iterator of all keys locally known about by the handler.
        """

    def resetLocalState():
        """Reset the local state (i.e. OpenPGP keyrings, trust database etc."""
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

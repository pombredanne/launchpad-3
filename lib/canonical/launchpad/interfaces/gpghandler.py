from zope.interface import Interface

__all__ = ['IGpgHandler']

class IGpgHandler(Interface):
    """Handler to perform GPG operations."""

    def verifySignature(content, signature=None, key=None):
        """Return whether or not the content is correctly signed.
        
        If signature is None, we assume content is clearsigned. Otherwise
        it stores the detached signature and content should contain the
        plain text in question.
        
        If key is None, we search launchpad's gpg key tables to find
        the key which might have signed it and attempt to verify it
        that way.
        
        :param content: The content to be verified
        :param signature: The signature (or None if content is clearsigned)
        :param key: The key to verify against (or None to search launchpad)
        
        :returns: True if content is correctly signed, False if it isn't
        Also returns the fingerprint of the key in question.
        """

    def importPubKey(pubkey, keyring=None):
        """Import the given public key.

        if keyring is None, we assume it as the default keyring.

        :param pubkey: public key content
        :param keyring: specific keyring name

        :returns: The key ID
        """
        
    def getKeyInfo(fingerprint):
        """Return additonal Key Info.

        Return None if not able to retrive the info

        :param fingerprint: key fingerprint (no spaces)

        :returns: keysize, algorithm, revoked
        """

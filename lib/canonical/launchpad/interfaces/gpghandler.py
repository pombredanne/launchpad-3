from zope.interface import Interface

__all__ = ['IGpgHandler']

class IGpgHandler(Interface):
    """Handler to perform GPG operations."""

    def verifySignature(content, signature=None, key=None):
        """Return whether or not the content is correctly signed.
        
        If signature is None, we assume content is clearsigned.
        
        If key is None, we search launchpad's gpg key tables to find
        the key which might have signed it and attempt to verify it
        that way.
        
        :param content: The content to be verified
        :param signature: The signature (or None if content is clearsigned)
        :param key: The key to verify against (or None to search launchpad)
        
        :returns: True if content is correctly signed, False if it isn't
        Also returns the fingerprint of the key in question.
        """

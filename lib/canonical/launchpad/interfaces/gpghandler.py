from zope.interface import Interface, Attribute

__all__ = ['IGPGHandler', 'IPymeSignature', 'IPymeKey']

class IGPGHandler(Interface):
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
        
        :returns: a PymeSignature object containing the signature information
        See IPymeSignature for further info.
        """

    def importKey(content):
        """Import the given public or secret key. We assume it as the
        default keyring.

        :param content: public or secret key content ASCII armored
        
        :returns: a PymeKey instance
        """

    def encryptContent(content, fingerprint):
        """Encrypt content for a given GPG key.

        :param content: data content
        :param fingerprint: key fingerprint

        :returns: encrypted data or None if failed
        """

    def decryptContent(content, password):
        """Decrypt content with the given password.

        :param content: encrypted data content
        :param password: raw passwrod to unlock the secret key in question 

        :returns: decrypted data or None if failed
        """

    def retrieveKey(fingerprint):
        """Retrieve key information from the local keyring, if key isn't
        present, import it from the key server before.

        :param fingerprint: key fingerprint

        :returns: operation result, PymeKey instance or Debug Info if result
        is False
        """


class IPymeSignature(Interface):
    """pyME signature container."""

    fingerprint = Attribute("Signer Fingerprint.")
    plain_data = Attribute("Plain Signed Text.")
    

class IPymeKey(Interface):
    """pyME key model.""" 

    fingerprint = Attribute("Key Fingerprint")
    algorithm = Attribute("Key Algorithm")
    revoked = Attribute("Key Revoked")
    keysize = Attribute("Key Size")
    keyid = Attribute("Pseudo Key ID, composed by last fingerprint 8 digits ")
    uids = Attribute("List containing only well formed and non-revoked UIDs")
    displayname = Attribute("Key displayname: <size><type>/<keyid>")

from zope.interface import Interface, Attribute

__all__ = ['IGPGHandler', 'IPymeSignature', 'IPymeKey']

class IGPGHandler(Interface):
    """Handler to perform GPG operations."""

    def verifySignature(content, signature=None):
        """Returns a PymeSignature objet if content is correctly signed
        or None. 
        
        If signature is None, we assume content is clearsigned. Otherwise
        it stores the detached signature and content should contain the
        plain text in question.

        content and signature must traditional strings. It's up to the caller
        to encode or decode properly.
    
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

    def local_keys():
        """Return an iterator of all keys locally known about by the handler.
        """

    def reset_local_state():
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
    keysize = Attribute("Key Size")
    keyid = Attribute("Pseudo Key ID, composed by last fingerprint 8 digits ")
    uids = Attribute("List containing only well formed and non-revoked UIDs")
    displayname = Attribute("Key displayname: <size><type>/<keyid>")
    owner_trust = Attribute("The owner trust")

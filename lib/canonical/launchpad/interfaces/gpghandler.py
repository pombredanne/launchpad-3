from zope.interface import Interface, Attribute

__all__ = ['IGpgHandler', 'IPymeSignature', 'IPymeKey']

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

    def importPubKey(pubkey):
        """Import the given public key. We assume it as the default keyring.

        :param pubkey: public key content
        
        :returns: a PymeKey instance
        """

    def getKeyIndex(fingerprint):
        """Retrieve Key Index Information from the KeyServer.

        It user urllib to retrive the key information page
        from 'pks' application, parse the content and instantiate
        a respective PymeKey object.

        Return None if not able to retrive the information

        :param fingerprint: key fingerprint (no spaces)

        :returns: info as [(size, type, id)] and uids as sorted list
        """

    def getPubKey(fingerprint):
        """Retrieve GPG public key ASCII armored

        It also uses urllib to retrive a public key from PKS systems

        return None if not able to get the public key

        :param fingerprint: key fingerprint (no spaces)
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
    keyid = Attribute("Pseudo Key ID (fpr last 8 digits)")
    uids = Attribute("List of contained UIDs.")

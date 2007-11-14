# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""OpenPGP key interfaces."""

__metaclass__ = type

__all__ = [
    'IGPGKey',
    'IGPGKeySet',
    'GPGKeyAlgorithm',
    ]

from zope.schema import Bool, Int, TextLine, Choice
from zope.interface import Interface, Attribute

from canonical.lazr import DBEnumeratedType, DBItem

from canonical.launchpad import _
from canonical.launchpad.interfaces.launchpad import IHasOwner
from canonical.launchpad.validators.gpg import valid_fingerprint, valid_keyid


# XXX: cprov 2004-10-04:
# (gpg+dbschema) the data structure should be rearranged to support 4 field
# needed: keynumber(1,16,17,20), keyalias(R,g,D,G), title and description
class GPGKeyAlgorithm(DBEnumeratedType):
    """
    GPG Compilant Key Algorithms Types:

    1 : "R", # RSA
    16: "g", # ElGamal
    17: "D", # DSA
    20: "G", # ElGamal, compromised

    FIXME
    Rewrite it according the experimental API retuning also a name attribute
    tested on 'algorithmname' attribute

    """

    R = DBItem(1, """
        R

        RSA""")

    LITTLE_G = DBItem(16, """
         g

         ElGamal""")

    D = DBItem(17, """
        D

        DSA""")

    G = DBItem(20, """
        G

        ElGamal, compromised""")


class IGPGKey(IHasOwner):
    """OpenPGP support"""
    id = Int(title=_("Database id"), required=True, readonly=True)
    keysize = Int(title=_("Keysize"), required=True)
    algorithm = Choice(title=_("Algorithm"), required=True,
            vocabulary='GpgAlgorithm')
    keyid = TextLine(title=_("OpenPGP key ID"), required=True,
            constraint=valid_keyid)
    fingerprint = TextLine(title=_("User Fingerprint"), required=True,
            constraint=valid_fingerprint)
    active = Bool(title=_("Active"), required=True)
    displayname = Attribute("Key Display Name")
    keyserverURL = Attribute("The URL to retrieve this key from the keyserver.")
    can_encrypt = Bool(title=_("Key can be used for encryption"),
                       required=True)


class IGPGKeySet(Interface):
    """The set of GPGKeys."""

    def new(ownerID, keyid, fingerprint, keysize,
            algorithm, active=True, can_encrypt=True):
        """Create a new GPGKey pointing to the given Person."""

    def get(key_id, default=None):
        """Return the GPGKey object for the given id.

        Return the given default if there's no object with the given id.
        """

    def getByFingerprint(fingerprint, default=None):
        """Return UNIQUE result for a given Key fingerprint including
        inactive ones.
        """

    def getGPGKeys(ownerid=None, active=True):
        """Return OpenPGP keys ordered by id.

        Optionally for a given owner and or a given status.
        """


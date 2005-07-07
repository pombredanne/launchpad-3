# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""GPG key interfaces."""

__metaclass__ = type

__all__ = [
    'IGPGKey',
    'IGPGKeySet',
    ]

from zope.schema import Bool, Int, TextLine, Choice
from zope.interface import Interface, Attribute
from canonical.launchpad import _

from canonical.launchpad.validators.gpg import valid_fingerprint, valid_keyid

class IGPGKey(Interface):
    """GPG support"""
    id = Int(title=_("Database id"), required=True, readonly=True)
    owner = Int(title=_("Owner"), required=True, readonly=True)
    keysize = Int(title=_("Keysize"), required=True)
    algorithm = Choice(title=_("Algorithm"), required=True,
            vocabulary='GpgAlgorithm')
    keyid = TextLine(title=_("GPG KeyID"), required=True,
            constraint=valid_keyid)
    fingerprint = TextLine(title=_("User Fingerprint"), required=True,
            constraint=valid_fingerprint)
    revoked = Bool(title=_("Revoked"), required=True)
    algorithmname = Attribute("The Algorithm Name")


class IGPGKeySet(Interface):
    """The set of GPGKeys."""

    def new(self, ownerID, keyid, fingerprint, keysize,
            algorithm, revoked):
        """Create a new GPGKey pointing to the given Person."""

    def get(id, default=None):
        """Return the GPGKey object for the given id.
        Return the given default if there's now object with the given id.
        """

    def getByFingerprint(fingerprint, default=None):
        """Return UNIQUE result for a given Key fingerprint."""

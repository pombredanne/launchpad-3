# Copyright 2004 Canonical Ltd.  All rights reserved.

from zope.schema import Bool, Int, Text, TextLine
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

#
# GPG Interfaces
#

class IGPGKey(Interface):
    """GPG support"""
    id = Int(title=_("Database id"), required=True, readonly=True)
    owner = Int(title=_("Owner"), required=True, readonly=True)
    keysize = Int(title=_("Keysize"), required=True)
    algorithm = Int(title=_("Algorithm"), required=True)

    keyid = TextLine(title=_("GPG KeyID"), required=True)
    pubkey = Text(title=_("Pub Key itself"), required=True)
    fingerprint = TextLine(title=_("User Fingerprint"), required=True)

    revoked = Bool(title=_("Revoked"), required=True)
    
    algorithmname = Attribute("The Algorithm Name")


class IGPGKeySet(Interface):
    """The set of GPGKeys."""

    def new(self, ownerID, keyid, pubkey, fingerprint, keysize,
            algorithm, revoked):
        """Create a new GPGKey pointing to the given Person."""

    def get(id, default=None):
        """Return the GPGKey object for the given id.
        Return the given default if there's now object with the given id.
        """

# Copyright 2005 Canonical Ltd. All rights reserved.

from zope.interface import Interface, Attribute
from pyme.constants import validity

__all__ = ['IKeyringTrustAnalyser']

__metaclass__ = type

class IKeyringTrustAnalyser(Interface):
    """A class to analyse gpg keyrings for trust levels."""

    def addTrustedKeyring(filename, ownertrust=validity.MARGINAL):
        """Add a keyring of keys belonging to people trusted to make
        good signatures."""

    def addOtherKeyring(filename):
        """Add a keyring of possibly suspect keys"""

    def getValidUids(minvalid=validity.MARGINAL):
        """Returns an iterator yielding (fingerprint, email) pairs,
        iterating for all valid user IDs in the keyring."""

    def findEmailClusters(minvalid=validity.MARGINAL):
        """Returns an iterator yielding sets of related email
        addresses.  Two email addresses are considered to be related
        if they appear as valid user IDs on a PGP key in the keyring."""

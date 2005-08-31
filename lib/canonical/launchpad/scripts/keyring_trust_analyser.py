# Copyright 2005 Canonical Ltd.  All rights reserved.

from zope.interface import implements
from zope.component import getUtility

from pyme.constants import validity

from canonical.launchpad.interfaces import IGPGHandler
from canonical.launchpad.validators.email import valid_email

__metaclass__ = type

__all__ = [
    'addTrustedKeyring',
    'addOtherKeyring',
    'getValidUids',
    'findEmailClusters'
    ]

def addTrustedKeyring(filename, ownertrust=validity.MARGINAL):
    """Add a keyring of keys belonging to people trusted to make
    good signatures.
    """
    gpg = getUtility(IGPGHandler)
    keys = gpg.importKeyringFile(filename)
    for key in keys:
        key.setOwnerTrust(ownertrust)

def addOtherKeyring(filename):
    """Add a keyring of possibly suspect keys"""
    gpg = getUtility(IGPGHandler)
    gpg.importKeyringFile(filename)

def getValidUids(minvalid=validity.MARGINAL):
    """Returns an iterator yielding (fingerprint, email) pairs,
    iterating for all valid user IDs in the keyring.
    """
    gpg = getUtility(IGPGHandler)
    gpg.checkTrustDb()
    for key in gpg.local_keys():
        for uid in key.uids:
            if (not uid.revoked and valid_email(uid.email) and
                uid.validity >= minvalid):
                yield key.fingerprint, uid.email

def findEmailClusters(minvalid=validity.MARGINAL):
    """Returns an iterator yielding sets of related email
    addresses.  Two email addresses are considered to be related
    if they appear as valid user IDs on a PGP key in the keyring.
    """
    emails = {}       # fingerprint -> set(emails)
    fingerprints = {} # email -> set(fingerprints)

    # get the valid UIDs
    for fpr, email in getValidUids(minvalid):
        fingerprints.setdefault(email, set()).add(fpr)
        emails.setdefault(fpr, set()).add(email)

    # find clusters of keys based on the presence of shared valid UIDs
    clusters = {} # fingerprint -> set(fingerprints)
    for fprs in fingerprints.itervalues():
        cluster = fprs.copy()
        for fpr in fprs:
            x = clusters.get(fpr)
            if x is not None:
                cluster.update(x)
        for fpr in cluster:
            clusters[fpr] = cluster

    # return email addresses belonging to each key cluster
    for cluster in clusters.itervalues():
        email_cluster = set()
        for fpr in cluster:
            email_cluster.update(emails[fpr])
        yield email_cluster

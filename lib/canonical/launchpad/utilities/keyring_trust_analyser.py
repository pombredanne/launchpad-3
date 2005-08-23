# Copyright 2005 Canonical Ltd.  All rights reserved.

from zope.interface import implements
from zope.component import getUtility

from pyme.constants import validity

from canonical.launchpad.interfaces import IGPGHandler, IKeyringTrustAnalyser
from canonical.launchpad.validators.email import valid_email

__metaclass__ = type

class KeyringTrustAnalyser:
    """A class to analyse gpg keyrings for trust levels."""

    implements(IKeyringTrustAnalyser)

    def __init__(self):
        self.gpg = getUtility(IGPGHandler)

    def addTrustedKeyring(self, filename, ownertrust=validity.MARGINAL):
        """See IKeyringTrustAnalyser"""
        keys = self.gpg.importKeyringFile(filename)
        for key in keys:
            key.owner_trust = ownertrust

    def addOtherKeyring(self, filename):
        """See IKeyringTrustAnalyser"""
        self.gpg.importKeyringFile(filename)

    def getValidUids(self, minvalid=validity.MARGINAL):
        """See IKeyringTrustAnalyser"""
        self.gpg.checkTrustDb()
        for key in self.gpg.local_keys():
            for uid in key.uids:
                if (not uid.revoked and valid_email(uid.email) and
                       uid.validity >= minvalid):
                    yield key.fpr, uid.email

    def findEmailClusters(self, minvalid=validity.MARGINAL):
        """See IKeyringTrustAnalyser."""
        emails = {}       # fingerprint -> email
        fingerprints = {} # email -> fingerprint

        # get the valid UIDs
        for fpr, email in self.getValidUids(minvalid):
            fingerprints.setdefault(email, set()).add(fpr)
            emails.setdefault(fpr, set()).add(email)

        # find clusters of keys based on the presence of shared valid UIDs
        clusters = {} # fingerprint -> set(fingerprints)
        for fprs in fingerprints:
            cluster = fprs.copy()
            for fpr in fprs:
                x = clusters.get(fpr)
                if x is not None:
                    cluster.extend(x)
            for fpr in cluster:
                clusters[fpr] = cluster

        # return email addresses belonging to each key cluster
        for cluster in clusters:
            email_cluster = set()
            for fpr in cluster:
                email_cluster.extend(emails[fpr])
            yield email_cluster

# Copyright 2005 Canonical Ltd.  All rights reserved.

from zope.interface import implements
from zope.component import getUtility

from pyme.constants import validity

from canonical.database.sqlbase import flush_database_updates

from canonical.launchpad.interfaces import (
    IGPGHandler, IPersonSet, IEmailAddressSet)
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

def _mergeOrAddEmails(personset, emailset, cluster):
    """Helper function for mergeClusters()

    The strategy for merging clusters is as follows:
     1. Find all Person objects attached to the given email addresses.
     2. If there is more than one Person object associated with the cluster,
        merge them into one (merge into Person with preferred email).
     3. If there are no Person objects associated with the cluster, create
        a new person.
     4. For each email address not associated with the person or awaiting
        validation, add it to the person in state NEW (unvalidated).

    This algorithm does not handle the case where two accounts have a
    preferred email.  This situation would indicate that users have
    logged in as both identities, and we don't want to kill accounts
    for no reason.
    """
    # get a list of Person objects associated with this address cluster
    people = set()
    for email in cluster:
        person = personset.getByEmail(email)
        if person:
            people.add(person)

    if len(people) > 1:
        # more than one Person object => account merge.

        # Check if any of the accounts have been used.
        # If one account has been used, we want to merge the others
        # into that one.
        # If more than one account has been used, bail.

        validpeople = set(person for person in people
                          if person.preferredemail is not None)
        if len(validpeople) > 1:
            # eek. multiple validated accounts!
            return None
        elif len(validpeople) == 1:
            person = validpeople.pop()
            people.remove(person)
        else:
            # no validated accounts -- pick one at random
            person = people.pop()

        # assign email addresses
        for otherperson in people:
            for email in emailset.getByPerson(otherperson):
                email.person = person
        flush_database_updates()

        # merge people
        for otherperson in people:
            personset.merge(otherperson, person)

    elif len(people) == 1:
        # one person: use that
        person = people.pop()
    else:
        # no person? create it.
        # We should have the display name from a key here ...
        person, email = personset.createPersonAndEmail(cluster.pop())

    # We now have one person.  Now add the missing addresses:
    existing = set(email.email for email in emailset.getByPerson(person))
    existing.update(person.unvalidatedemails)
    for newemail in cluster.difference(existing):
        emailset.new(newemail, person)

    return person

def mergeClusters(clusters, ztm=None):
    """Merge accounts for clusters of addresses.

    The first argument is an iterator returning sets of email addresses.
    """
    personset = getUtility(IPersonSet)
    emailset = getUtility(IEmailAddressSet)
    for cluster in clusters:
        if not cluster: continue

        if ztm: ztm.begin()
        _mergeOrAddEmails(personset, emailset, cluster)
        if ztm: ztm.commit()

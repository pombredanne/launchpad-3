# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""GPG keys used for testing.

There are two GPG keys located in the 'gpgkeys' sub directory, one for
Sample Person and for Foo Bar. The passwords for the secret keys are
'test'.

Before they are used in tests they need to be imported, so that
GpgHandlder knows about them.  import_public_test_keys() imports all
public keys available, while import_public_key(email_addr) only imports
the key associated with that specific email address.
"""


__metaclass__ = type

import os
from zope.component import getUtility
from canonical.lp.dbschema import GPGKeyAlgorithms
from canonical.launchpad.interfaces import IGPGKeySet, IGpgHandler, IPersonSet

gpgkeysdir = os.path.join(os.path.dirname(__file__), 'gpgkeys')

def import_public_key(email_addr):
    """Imports the public key related to the given email address."""
    gpghandler = getUtility(IGpgHandler)
    personset = getUtility(IPersonSet)

    pubkey = open(os.path.join(gpgkeysdir, email_addr + '.pub')).read()
    fingerprint = gpghandler.importPubKey(pubkey)               

    person = personset.getByEmail(email_addr)
    for gpgkey in person.gpgkeys:
        if gpgkey.fingerprint == fingerprint:
            # If the key's already added to the database, do nothing.
            return
        
    # Insert the key into the database.
    keysize, algorithm, revoked = gpghandler.getKeyInfo(fingerprint)
    getUtility(IGPGKeySet).new(
        ownerID=personset.getByEmail(email_addr).id,
        keyid=fingerprint[-8:],
        pubkey=pubkey,
        fingerprint=fingerprint,
        keysize=keysize,
        algorithm=GPGKeyAlgorithms.items[algorithm],
        revoked=revoked)

def import_public_test_keys():
    """Imports all the public keys located in gpgkeysdir into the db."""
    for name in os.listdir(gpgkeysdir):
        if name.endswith('.pub'):
            import_public_key(name[:-4])


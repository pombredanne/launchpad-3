# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""GPG keys used for testing.

There are two GPG keys located in the 'gpgkeys' sub directory, one for
Sample Person and for Foo Bar. The passwords for the secret keys are
'test'.

Before they are used in tests they need to be imported, so that
GpgHandler knows about them.  import_public_test_keys() imports all
public keys available, while import_public_key(email_addr) only imports
the key associated with that specific email address.

Secret keys are also imported into the local key ring, they are used for
decrypt data in pagetests.
"""


__metaclass__ = type

import os
from zope.component import getUtility
from canonical.lp.dbschema import GPGKeyAlgorithm
from canonical.launchpad.interfaces import IGPGKeySet, IGPGHandler, IPersonSet

gpgkeysdir = os.path.join(os.path.dirname(__file__), 'gpgkeys')

def import_public_key(email_addr):
    """Imports the public key related to the given email address."""
    gpghandler = getUtility(IGPGHandler)
    personset = getUtility(IPersonSet)

    pubkey = test_pubkey_from_email(email_addr)
    key = gpghandler.importKey(pubkey)               

    person = personset.getByEmail(email_addr)
    for gpgkey in person.gpgkeys:
        if gpgkey.fingerprint == key.fingerprint:
            # If the key's already added to the database, do nothing.
            return
        
    # Insert the key into the database.
    getUtility(IGPGKeySet).new(
        ownerID=personset.getByEmail(email_addr).id,
        keyid=key.keyid,
        fingerprint=key.fingerprint,
        keysize=key.keysize,
        algorithm=GPGKeyAlgorithm.items[key.algorithm],
        active=(not key.revoked))

def iter_test_key_emails():
    """Iterates over the email addresses for the keys in the gpgkeysdir."""
    for name in os.listdir(gpgkeysdir):
        if name.endswith('.pub'):
            yield name[:-4]

def import_public_test_keys():
    """Imports all the public keys located in gpgkeysdir into the db."""
    for email in iter_test_key_emails():
        import_public_key(email)

def import_secret_test_key():
    """Imports the secret key located in gpgkeysdir into local keyring."""
    gpghandler = getUtility(IGPGHandler)

    seckey = open(os.path.join(gpgkeysdir, 'test@canonical.com.sec')).read()
    gpghandler.importKey(seckey)               

def test_pubkey_file_from_email(email_addr):
    """Get the file name for a test pubkey by email address."""
    return os.path.join(gpgkeysdir, email_addr + '.pub')

def test_pubkey_from_email(email_addr):
    """Get the on disk content for a test pubkey by email address."""
    return open(test_pubkey_file_from_email(email_addr)).read()

def test_keyrings():
    """Iterate over the filenames for test keyrings."""
    for name in os.listdir(gpgkeysdir):
        if name.endswith('.gpg'):
            yield os.path.join(gpgkeysdir, name)



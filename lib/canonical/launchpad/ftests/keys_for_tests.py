# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""OpenPGP keys used for testing.

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
from cStringIO import StringIO

from zope.component import getUtility

import gpgme

from canonical.launchpad.interfaces import (
    IGPGKeySet, IGPGHandler, IPersonSet, GPGKeyAlgorithm)

gpgkeysdir = os.path.join(os.path.dirname(__file__), 'gpgkeys')

def import_public_key(email_addr):
    """Imports the public key related to the given email address."""
    gpghandler = getUtility(IGPGHandler)
    personset = getUtility(IPersonSet)

    pubkey = test_pubkey_from_email(email_addr)
    key = gpghandler.importPublicKey(pubkey)

    # Strip out any '-passwordless' annotation from the email addresses.
    email_addr = email_addr.replace('-passwordless', '')

    # Some of the keys shouldn't be inserted into the db.
    if email_addr.endswith('do-not-insert-into-db'):
        return

    person = personset.getByEmail(email_addr)

    # Some of the sample keys do not have corresponding Launchpad
    # users, so ignore them.
    if not person:
        return

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

def import_secret_test_key(keyfile='test@canonical.com.sec'):
    """Imports the secret key located in gpgkeysdir into local keyring.

    :param keyfile: The name of the file to be imported.
    """
    # We import the secret key manually here because this is the only place
    # where we import a secret key and thus we don't need an API for this
    # on GPGHandler.

    # Make sure that gpg-agent doesn't interfere.
    if 'GPG_AGENT_INFO' in os.environ:
        del os.environ['GPG_AGENT_INFO']
    seckey = open(os.path.join(gpgkeysdir, keyfile)).read()
    context = gpgme.Context()
    context.armor = True
    newkey = StringIO(seckey)
    result = context.import_(newkey)

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

def decrypt_content(content, password):
    """Return the decrypted content or None if failed

    content and password must be traditional strings. It's up to
    the caller to encode or decode properly.

    :content: encrypted data content
    :password: unicode password to unlock the secret key in question
    """
    if isinstance(password, unicode):
        raise TypeError('Password cannot be Unicode.')

    if isinstance(content, unicode):
        raise TypeError('Content cannot be Unicode.')

    # setup context
    ctx = gpgme.Context()
    ctx.armor = True

    # setup containers
    cipher = StringIO(content)
    plain = StringIO()

    def passphrase_cb(uid_hint, passphrase_info, prev_was_bad, fd):
        os.write(fd, '%s\n' % password)

    ctx.passphrase_cb = passphrase_cb

    # Do the deecryption.
    try:
        ctx.decrypt(cipher, plain)
    except gpgme.GpgmeError:
        return None

    return plain.getvalue()


def sign_content(content, key_fingerprint, password,
                 mode=gpgme.SIG_MODE_CLEAR):
    """Signs content with a given GPG key.

    :param content: The content to sign.
    :param key_fingerprint: The fingerprint of the key to use when
        signing the content.
    :param password: The password to the key identified by key_fingerprint.
    :param mode: The type of GPG signature to produce.
    :return: The ASCII-armored signature for the content.
    """

    # Find the key and make it the only one allowed to sign content
    # during this session.
    ctx = gpgme.Context()
    ctx.armor = True
    key = ctx.get_key(key_fingerprint)
    ctx.signers = [key]

    # Set up containers.
    plaintext = StringIO(content)
    signature = StringIO()

    def passphrase_cb(uid_hint, passphrase_info, prev_was_bad, fd):
        os.write(fd, '%s\n' % password)  
    ctx.passphrase_cb = passphrase_cb

    # Sign the text.
    try:
        new_sig = ctx.sign(plaintext, signature, mode)
    except gpgme.GpgmeError: 
        return None

    return signature.getvalue()

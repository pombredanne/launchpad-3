# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

# standard
import os
import tempfile

# zope
from zope.interface import implements

# interface
from canonical.launchpad.interfaces import IGpgHandler

# pyme 
from pyme import core


class GpgHandler(object):
    """See IGpgHandler."""

    implements(IGpgHandler)
    
    def verifySignature(self, content, signature=None, key=None):
        """See IGpgHandler."""

        c = core.Context()

        # from `info gpgme` about gpgme_op_verify(SIG, SIGNED_TEXT, PLAIN):
        #
        # If SIG is a detached signature, then the signed text should be
        # provided in SIGNED_TEXT and PLAIN should be a null pointer.
        # Otherwise, if SIG is a normal (or cleartext) signature,
        # SIGNED_TEXT should be a null pointer and PLAIN should be a
        # writable data object that will contain the plaintext after
        # successful verification.

        if signature:
            # store detach-sig
            sig = core.Data(signature.encode('ascii'))
            # store the content
            plain = core.Data(content.encode('ascii'))        
            # process it
            c.op_verify(sig, plain, None)
        else:
            # store clearsigned signature
            sig = core.Data(content.encode('ascii'))
            # writeable content
            plain = core.Data()
            # process it
            c.op_verify(sig, None, plain)
        
        result = c.op_verify_result()

        # XXX cprov 20050328
        # it doesn't support multiple signatures yet
        signature = result.signatures

        # signature.status == 0 means "Ok"
        if signature.status != 0:
            return None, None

        fingerprint = signature.fpr
        plain.seek(0,0)
        plain_data = plain.read()
        
        return fingerprint, plain_data

    def importPubKey(self, pubkey, keyring=None):
        """See IGpgHandler."""

        # XXX cprov 20050415
        # Support multiple keyring is considered obsolete in the GPGME
        # approach. For information on how to handle multiple contexts,
        # see W. Koch's interesting comment at:
        # http://lists.gnupg.org/pipermail/gnupg-users/2005-February/024755.html
        c = core.Context()
        c.set_armor(1)

        newkey = core.Data(pubkey.encode('ascii'))

        c.op_import(newkey)

        result = c.op_import_result()
        
        if result.considered == 0:
            return 

        return result.imports.fpr

        
    def getKeyInfo(self, fingerprint):
        """See IGpgHandler."""
        c = core.Context()

        key = c.get_key(fingerprint, 0).subkeys

        if key == None:
            return None, None, None
        
        keysize = key.length
        algorithm = key.pubkey_algo
        revoked = key.revoked
        
        return keysize, algorithm, revoked

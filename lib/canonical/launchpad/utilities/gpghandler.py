# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

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

        # XXX cprov 20050328
        # Missed support for deattached signatures and key checks       
        c = core.Context()
        sig = core.Data(content.encode('ascii'))

        plain = core.Data()
        
        c.op_verify(sig, None, plain)

        result = c.op_verify_result()

        # XXX cprov 20050328
        # Do not support multiple signature yet
        signature = result.signatures

        # signature.status == 0 means "Ok"
        if signature.status == 0:
            fingerprint = signature.fpr
            plain.seek(0,0)
            plain_coc = plain.read()
        else:
            fingerprint = None
            plain_coc = None
        
        return fingerprint, plain_coc


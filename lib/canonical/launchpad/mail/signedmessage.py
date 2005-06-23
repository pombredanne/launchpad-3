# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Classes for simpler handling of PGP signed email messages."""

__metaclass__ = type

import email.Message
import re

from zope.interface import implements

from canonical.launchpad.interfaces import ISignedMessage

signed_re = re.compile(
    r'-----BEGIN PGP SIGNED MESSAGE-----'
    '.*?(?:\r\n|\n)(?:\r\n|\n)(.*)(?:\r\n|\n)'
    '(-----BEGIN PGP SIGNATURE-----'
    '.*'
    '-----END PGP SIGNATURE-----)',
    re.DOTALL)

class SignedMessage(email.Message.Message):
    """Provides easy access to signed content and the signature"""
    implements(ISignedMessage)

    def _get_signature_signed_message(self):
        """Returns the PGP signature and content that's signed.
       
        The signature is returned as a string, and the content is
        returned as a message instance.

        If the message isn't signed, both signature and the content is
        None.
        """
        signed_content = signature = None
        payload = self.get_payload() 
        if self.is_multipart():
            if len(payload) == 2:
                content_part, signature_part = payload
                sig_content_type = signature_part.get_content_type()
                if sig_content_type == 'application/pgp-signature':
                    signed_content = content_part.as_string()
                    signature = signature_part.get_payload()
        else:
            match = signed_re.search(payload)
            if match is not None:
                # Add a new line so that a message with no headers will
                # be created.
                signed_content = "\n" + match.group(1)
                signature = match.group(2)

        if signed_content is not None:
            signed_message = email.message_from_string(signed_content,
                                                       self.__class__)
        else:
            signed_message = None

        return signature, signed_message

    def signedMessage(self):
        """Returns the PGP signed content as a message.
        
        Returns None if the message wasn't signed.
        """
        signature, signed_message = self._get_signature_signed_message()
        return signed_message
    signedMessage = property(signedMessage)

    def signedContent(self):
        """Returns the PGP signed content as a string.
        
        Returns None if the message wasn't signed.
        """
        signature, signed_message = self._get_signature_signed_message()
        if signed_message is None:
            return None
        elif len(signed_message.keys()) == 0:
            return signed_message.get_payload()
        else:
            return signed_message.as_string()
    signedContent = property(signedContent)

    def signature(self):
        """Returns the PGP signature used to sign the message.
        
        Returns None if the message wasn't signed.
        """
        signature, signed_message = self._get_signature_signed_message()
        return signature
    signature = property(signature)

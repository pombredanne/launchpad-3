# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Classes for simpler handling of PGP signed email messages."""

__metaclass__ = type

__all__ = [
    'SignedMessage',
    'signed_message_from_string',
    ]

import email
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

# Regexp for matching the signed content in multipart messages.
multipart_signed_content = (
    r'%(boundary)s\n(?P<signed_content>.*?)\n%(boundary)s\n.*?\n%(boundary)s')

# Lines that start with '-' are escaped with '- '.
dash_escaped = re.compile('^- ', re.MULTILINE)


def signed_message_from_string(string):
    """Parse the string and return a SignedMessage.

    It makes sure that the SignedMessage instance has access to the
    parsed string.
    """
    msg = email.message_from_string(string, _class=SignedMessage)
    msg.parsed_string = string
    return msg


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
                    # We need to extract the signed content from the
                    # parsed string, since content_part.as_string()
                    # isn't guarenteed to return the exact string it was
                    # created from.
                    boundary = '--' + self.get_boundary()
                    match = re.search(
                        multipart_signed_content % {'boundary': boundary},
                        self.parsed_string, re.DOTALL)
                    signed_content = match.group('signed_content')
                    signature = signature_part.get_payload()
        else:
            match = signed_re.search(payload)
            if match is not None:
                # Add a new line so that a message with no headers will
                # be created.
                signed_content_unescaped = "\n" + match.group(1)
                signed_content = dash_escaped.sub('', signed_content_unescaped)
                signature = match.group(2)

        return signature, signed_content

    @property
    def signedMessage(self):
        """Returns the PGP signed content as a message.

        Returns None if the message wasn't signed.
        """
        signature, signed_content = self._get_signature_signed_message()
        if signed_content is None:
            return None
        else:
            return signed_message_from_string(signed_content)

    @property
    def signedContent(self):
        """Returns the PGP signed content as a string.

        Returns None if the message wasn't signed.
        """
        signature, signed_content = self._get_signature_signed_message()
        return signed_content

    @property
    def signature(self):
        """Returns the PGP signature used to sign the message.

        Returns None if the message wasn't signed.
        """
        signature, signed_message = self._get_signature_signed_message()
        return signature

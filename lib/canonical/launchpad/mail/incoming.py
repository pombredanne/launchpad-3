# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Functions dealing with mails coming into Launchpad."""

__metaclass__ = type

import email.Utils
from zope.component import getUtility
from canonical.launchpad.interfaces import IPerson, IGpgHandler
from canonical.launchpad.utilities import GpgHandler
from canonical.launchpad.helpers import setupInteraction
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility


def authenticateEmail(mail):
    """Authenticates an email by verifying the PGP signature.

    The mail is expected to be an ISignedMessage.
    """
    signature = mail.signature
    signed_content = mail.signedContent

    name, email_addr = email.Utils.parseaddr(mail['From'])
    authutil = getUtility(IPlacelessAuthUtility)
    principal = authutil.getPrincipalByLogin(email_addr)
    
    # Check that sender is registered in Launchpad and the email is signed.
    if principal is None or signature is None:
        setupInteraction(authutil.unauthenticatedPrincipal())
        return

    person = IPerson(principal)
    gpghandler = getUtility(IGpgHandler)
    fingerprint, plain = gpghandler.verifySignature(signed_content, signature)
    if fingerprint is not None:
        # Log in the user if the key used to sign belongs to him.
        for gpgkey in person.gpgkeys:
            if gpgkey.fingerprint == fingerprint:
                setupInteraction(principal, email_addr)
                return principal

    # The GPG signature couldn't be verified  
    setupInteraction(authutil.unauthenticatedPrincipal())

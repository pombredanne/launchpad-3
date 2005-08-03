# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Functions dealing with mails coming into Launchpad."""

__metaclass__ = type

from logging import getLogger
from cStringIO import StringIO as cStringIO
from email.Utils import getaddresses, parseaddr
import email.Errors

import transaction
from zope.component import getUtility, queryUtility

from canonical.launchpad.interfaces import (IPerson, IGPGHandler, 
    IMailHandler, IMailBox, ILibraryFileAliasSet)
from canonical.launchpad.helpers import (setupInteraction,
    get_filename_from_message_id)
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
from canonical.launchpad.mail.signedmessage import SignedMessage
from canonical.launchpad.mailnotification import notify_errors_list


class InvalidSignature(Exception):
    """The signature failed to validate."""


def authenticateEmail(mail):
    """Authenticates an email by verifying the PGP signature.

    The mail is expected to be an ISignedMessage.
    """
    signature = mail.signature
    signed_content = mail.signedContent

    name, email_addr = parseaddr(mail['From'])
    authutil = getUtility(IPlacelessAuthUtility)
    principal = authutil.getPrincipalByLogin(email_addr)

    # Check that sender is registered in Launchpad and the email is signed.
    if principal is None:
        setupInteraction(authutil.unauthenticatedPrincipal())
        return
    elif signature is None:
        #XXX: When DifferentPrincipalsSameUser is implemented, a weakly
        #     authenticated principal should be used. At the moment we have to
        #     do all permission checks in the code instead of using security
        #     adapter. -- Bjorn Tillenius, 2005-06-06
        setupInteraction(principal, email_addr)
        return principal

    person = IPerson(principal)
    gpghandler = getUtility(IGPGHandler)
    sig = gpghandler.verifySignature(signed_content, signature)
    if sig.fingerprint is not None:
        # Log in the user if the key used to sign belongs to him.
        for gpgkey in person.gpgkeys:
            if gpgkey.fingerprint == sig.fingerprint:
                setupInteraction(principal, email_addr)
                return principal
        # The key doesn't belong to the user.
        raise InvalidSignature(
            "The key used to sign the email doesn't belong to the user.")
    else:
        raise InvalidSignature("Signature couldn't be verified.")

    # The GPG signature couldn't be verified  
    setupInteraction(authutil.unauthenticatedPrincipal())


def handleMail(trans=transaction):
    mailbox = getUtility(IMailBox)
    mailbox.open()
    for mail_id, raw_mail in mailbox.items():
        trans.begin()
        try:
            mail = email.message_from_string(raw_mail, _class=SignedMessage)
        except email.Errors.MessageError, error:
            mailbox.delete(mail_id)
            log = getLogger('canonical.launchpad.mail')
            log.warn( "Couldn't convert email to email.Message", exc_info=True)
            continue

        # File the raw_mail in the Librarian
        file_name = get_filename_from_message_id(mail['Message-Id'])
        file_alias = getUtility(ILibraryFileAliasSet).create(
                file_name, len(raw_mail),
                cStringIO(raw_mail), 'message/rfc822')
        # If something goes wrong when handling the mail, the
        # transaction will be aborted. Therefore we need to commit the
        # transaction now, to ensure that the mail gets stored in the
        # Librarian.
        trans.commit()
        trans.begin()

        try:
            principal = authenticateEmail(mail)
        except InvalidSignature, error:
            mailbox.delete(mail_id)
            notify_errors_list(
                "Invalid signature for %s:\n    %s" % (mail['From'],
                                                       str(error)),
                file_alias)
            continue
        if principal is None:
            mailbox.delete(mail_id)
            notify_errors_list('Unknown user: %s ' % mail['From'], file_alias) 
            continue

        # Extract the domain the mail was sent to. Mails sent to
        # Launchpad should have an X-Original-To header.
        if mail.has_key('X-Original-To'):
            addresses = [mail['X-Original-To']]
        else:
            log = getLogger('canonical.launchpad.mail')
            log.warn(
                "No X-Original-To header was present in email: %s" %
                 file_alias.url)
            # Process all addresses found as a fall back.
            cc = mail.get_all('cc') or []
            to = mail.get_all('to') or []
            names_addresses = getaddresses(to + cc)
            addresses = [addr for name, addr in names_addresses]

        handler = None
        for email_addr in addresses:
            user, domain = email_addr.split('@')
            handler = queryUtility(IMailHandler, name=domain)
            if handler is not None:
                break

        if handler is None:
            mailbox.delete(mail_id)
            notify_errors_list(
                "No handler registered for '%s' " % (', '.join(addresses)),
                file_alias)
            continue

        try:
            handled = handler.process(mail, email_addr, file_alias)
        except Exception, error:
            # The handler shouldn't raise any exceptions. It it
            # does, it's a programming error.
            mailbox.delete(mail_id)
            notify_errors_list(
                "An exception was raised inside the handler: %s: %s " % (
                    error.__class__.__name__, str(error)),
                file_alias) 
            continue


        if not handled:         
            notify_errors_list(
                "Handler found, but message was not handled: %s" % (
                    mail['From'], ),
                file_alias) 

        # Let's commit the transaction before we delete the mail, since
        # we're favouring receiving the same mail twice in the case of
        # an error, over loosing the processing of a message by deleting
        # the message before committing.
        trans.commit()
        mailbox.delete(mail_id)

    mailbox.close()

# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Functions dealing with mails coming into Launchpad."""

__metaclass__ = type

from logging import getLogger
from cStringIO import StringIO as cStringIO
from email.Utils import getaddresses, parseaddr
import email.Errors
import re

import transaction
from zope.component import getUtility, queryUtility

from canonical.launchpad.interfaces import (IPerson, IGPGHandler, 
    IMailHandler, IMailBox, ILibraryFileAliasSet)
from canonical.launchpad.helpers import (setupInteraction,
    get_filename_from_message_id)
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
from canonical.launchpad.mail.signedmessage import SignedMessage
from canonical.launchpad.mailnotification import notify_errors_list


# Match '\n' and '\r' line endings. That is, all '\r' that are not
# followed by a # '\n', and all '\n' that are not preceded by a '\r'.
non_canonicalised_line_endings = re.compile('((?<!\r)\n)|(\r(?!\n))')


def canonicalise_line_endings(text):
    r"""Canonicalise the line endings to '\r\n'.

        >>> canonicalise_line_endings('\n\nfoo\nbar\rbaz\r\n')
        '\r\n\r\nfoo\r\nbar\r\nbaz\r\n'

        >>> canonicalise_line_endings('\r\rfoo\r\nbar\rbaz\n')
        '\r\n\r\nfoo\r\nbar\r\nbaz\r\n'

        >>> canonicalise_line_endings('\r\nfoo\r\nbar\nbaz\r')
        '\r\nfoo\r\nbar\r\nbaz\r\n'
    """
    if non_canonicalised_line_endings.search(text):
        text = non_canonicalised_line_endings.sub('\r\n', text)
    return text


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
    sig = gpghandler.verifySignature(
        canonicalise_line_endings(signed_content), signature)
    if sig is None:
        # verifySignature failed to verify the signature.
        raise InvalidSignature("Signature couldn't be verified.")

    # Log in the user if the key used to sign belongs to him.
    for gpgkey in person.gpgkeys:
        if gpgkey.fingerprint == sig.fingerprint:
            setupInteraction(principal, email_addr)
            return principal
    # The key doesn't belong to the user.
    raise InvalidSignature(
        "The key used to sign the email doesn't belong to the user.")

    # The OpenPGP signature couldn't be verified  
    setupInteraction(authutil.unauthenticatedPrincipal())


def handleMail(trans=transaction):
    # First we define an error handler. We define it as a local
    # function, to avoid having to pass a lot of parameters.
    def _handle_error(error_msg, file_alias_url):
        """Handles error occuring in handleMail's for-loop.

        It does the following:

            * deletes the current mail from the mailbox
            * sends error_msg and file_alias_url to the errors list
            * commits the current transaction to ensure that the
              message gets sent.
        """
        mailbox.delete(mail_id)
        notify_errors_list(error_msg, file_alias_url)
        trans.commit()

    mailbox = getUtility(IMailBox)
    mailbox.open()
    for mail_id, raw_mail in mailbox.items():
        trans.begin()
        try:
            mail = email.message_from_string(raw_mail, _class=SignedMessage)
        except email.Errors.MessageError, error:
            mailbox.delete(mail_id)
            log = getLogger('canonical.launchpad.mail')
            log.warn("Couldn't convert email to email.Message", exc_info=True)
            continue

        # File the raw_mail in the Librarian
        file_name = get_filename_from_message_id(mail['Message-Id'])
        file_alias = getUtility(ILibraryFileAliasSet).create(
                file_name, len(raw_mail),
                cStringIO(raw_mail), 'message/rfc822')
        # Let's save the url of the file alias, otherwise we might not
        # be able to access it later if we get a DB exception.
        file_alias_url = file_alias.url

        # If something goes wrong when handling the mail, the
        # transaction will be aborted. Therefore we need to commit the
        # transaction now, to ensure that the mail gets stored in the
        # Librarian.
        trans.commit()
        trans.begin()

        # If the Return-Path header is '<>', it probably means that it's
        # a bounce from a message we sent.
        if mail['Return-Path'] == '<>':
            _handle_error("Message had an empty Return-Path.", file_alias_url)
            continue

        try:
            principal = authenticateEmail(mail)
        except InvalidSignature, error:
            _handle_error(
                "Invalid signature for %s:\n    %s" % (mail['From'],
                                                       str(error)),
                file_alias_url)
            continue

        if principal is None:
            _handle_error('Unknown user: %s ' % mail['From'], file_alias_url)
            continue

        # Extract the domain the mail was sent to. Mails sent to
        # Launchpad should have an X-Original-To header.
        if mail.has_key('X-Original-To'):
            addresses = [mail['X-Original-To']]
        else:
            log = getLogger('canonical.launchpad.mail')
            log.warn(
                "No X-Original-To header was present in email: %s" %
                 file_alias_url)
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
            _handle_error(
                "No handler registered for '%s' " % (', '.join(addresses)),
                file_alias_url)
            continue

        try:
            handled = handler.process(mail, email_addr, file_alias)
        except:
            # The handler shouldn't raise any exceptions. If it
            # does, it's a programming error. We log the error instead
            # of sending an email in order to keep it as simple as
            # possible, we don't want any new exceptions raised here.
            mailbox.delete(mail_id)
            log = getLogger('canonical.launchpad.mail')
            log.error(
                "An exception was raised inside the handler: %s" % (
                    file_alias_url),
                exc_info=True)
            continue


        if not handled:
            _handle_error(
                "Handler found, but message was not handled: %s" % (
                    mail['From'], ),
                file_alias_url) 
            continue

        # Let's commit the transaction before we delete the mail, since
        # we're favouring receiving the same mail twice in the case of
        # an error, over loosing the processing of a message by deleting
        # the message before committing.
        trans.commit()
        mailbox.delete(mail_id)

    mailbox.close()

# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Functions dealing with mails coming into Launchpad."""

__metaclass__ = type

from logging import getLogger
from cStringIO import StringIO as cStringIO
from email.Utils import getaddresses, parseaddr
import email.Errors
import re
import sys

import transaction
from zope.component import getUtility
from zope.interface import directlyProvides, directlyProvidedBy

from canonical.uuid import generate_uuid
from canonical.launchpad.interfaces import (
    GPGVerificationError, IGPGHandler, ILibraryFileAliasSet, IMailBox,
    IPerson, IWeaklyAuthenticatedPrincipal)
from canonical.launchpad.webapp.errorlog import (
    ErrorReportingUtility, ScriptRequest)
from canonical.launchpad.webapp.interaction import get_current_principal
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
from canonical.launchpad.webapp.interaction import setupInteraction
from canonical.launchpad.mail.commands import get_error_message
from canonical.launchpad.mail.handlers import mail_handlers
from canonical.launchpad.mail.signedmessage import signed_message_from_string
from canonical.launchpad.mailnotification import (
    send_process_error_notification)
from canonical.librarian.interfaces import UploadFailed

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
        # Mark the principal so that application code can check that the
        # user was weakly authenticated.
        directlyProvides(
            principal, directlyProvidedBy(principal),
            IWeaklyAuthenticatedPrincipal)
        setupInteraction(principal, email_addr)
        return principal

    person = IPerson(principal)
    gpghandler = getUtility(IGPGHandler)
    try:
        sig = gpghandler.getVerifiedSignature(
            canonicalise_line_endings(signed_content), signature)
    except GPGVerificationError, e:
        # verifySignature failed to verify the signature.
        raise InvalidSignature("Signature couldn't be verified: %s" % str(e))

    for gpgkey in person.gpgkeys:
        if gpgkey.fingerprint == sig.fingerprint:
            break
    else:
        # The key doesn't belong to the user. Mark the principal so that the
        # application code knows that the key used to sign the email isn't
        # associated with the authenticated user.
        directlyProvides(
            principal, directlyProvidedBy(principal),
            IWeaklyAuthenticatedPrincipal)

    setupInteraction(principal, email_addr)
    return principal


class MailErrorUtility(ErrorReportingUtility):
    """An error utility that doesn't ignore exceptions."""

    _ignored_exceptions = set()

    def __init__(self):
        super(MailErrorUtility, self).__init__()
        # All errors reported for incoming email will have 'EMAIL'
        # appended to the configured oops_prefix.
        self.setOopsToken('EMAIL')


def report_oops(file_alias_url=None, error_msg=None):
    """Record an OOPS for the current exception and return the OOPS ID."""
    info = sys.exc_info()
    properties = []
    if file_alias_url is not None:
        properties.append(('Sent message', file_alias_url))
    if error_msg is not None:
        properties.append(('Error message', error_msg))
    request = ScriptRequest(properties)
    request.principal = get_current_principal()
    errorUtility = MailErrorUtility()
    errorUtility.raising(info, request)
    assert request.oopsid is not None, (
        'MailErrorUtility failed to generate an OOPS.')
    return request.oopsid


def handleMail(trans=transaction):
    # First we define an error handler. We define it as a local
    # function, to avoid having to pass a lot of parameters.
    # pylint: disable-msg=W0631
    def _handle_error(error_msg, file_alias_url, notify=True):
        """Handles error occuring in handleMail's for-loop.

        It does the following:

            * deletes the current mail from the mailbox
            * records an OOPS with error_msg and file_alias_url
              if notify is True
            * commits the current transaction to ensure that the
              message gets sent
        """
        mailbox.delete(mail_id)
        if notify:
            msg = signed_message_from_string(raw_mail)
            oops_id = report_oops(
                file_alias_url=file_alias_url,
                error_msg=error_msg)
            send_process_error_notification(
                msg['From'],
                'Submit Request Failure',
                get_error_message('oops.txt', oops_id=oops_id),
                msg)
        trans.commit()

    log = getLogger('process-mail')
    mailbox = getUtility(IMailBox)
    log.info("Opening the mail box.")
    mailbox.open()
    try:
        for mail_id, raw_mail in mailbox.items():
            log.info("Processing mail %s" % mail_id)
            try:
                file_alias_url = None
                trans.begin()

                # File the raw_mail in the Librarian
                file_name = generate_uuid() + '.txt'
                try:
                    file_alias = getUtility(ILibraryFileAliasSet).create(
                            file_name, len(raw_mail),
                            cStringIO(raw_mail), 'message/rfc822')
                except UploadFailed:
                    # Something went wrong in the Librarian. It could be
                    # that it's not running, but not necessarily. Log
                    # the error and skip the message, but don't delete
                    # it.
                    log.exception('Upload to Librarian failed')
                    continue

                # Let's save the url of the file alias, otherwise we might not
                # be able to access it later if we get a DB exception.
                file_alias_url = file_alias.http_url

                # If something goes wrong when handling the mail, the
                # transaction will be aborted. Therefore we need to commit the
                # transaction now, to ensure that the mail gets stored in the
                # Librarian.
                trans.commit()
                trans.begin()

                try:
                    mail = signed_message_from_string(raw_mail)
                except email.Errors.MessageError, error:
                    mailbox.delete(mail_id)
                    log = getLogger('canonical.launchpad.mail')
                    log.warn(
                        "Couldn't convert email to email.Message: %s" % (
                            file_alias_url, ),
                        exc_info=True)
                    continue


                # If the Return-Path header is '<>', it probably means
                # that it's a bounce from a message we sent.
                if mail['Return-Path'] == '<>':
                    _handle_error(
                        "Message had an empty Return-Path.",
                        file_alias_url, notify=False
                        )
                    continue
                if mail.get_content_type() == 'multipart/report':
                    # Mails with a content type of multipart/report are
                    # generally DSN messages and should be ignored.
                    _handle_error(
                        "Got a multipart/report message.",
                        file_alias_url, notify=False)
                    continue

                try:
                    principal = authenticateEmail(mail)
                except InvalidSignature, error:
                    _handle_error(
                        "Invalid signature for %s:\n    %s" % (mail['From'],
                                                               str(error)),
                        file_alias_url)
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
                    handler = mail_handlers.get(domain)
                    if handler is not None:
                        break

                if handler is None:
                    _handle_error(
                        "No handler registered for '%s' " % (
                            ', '.join(addresses)),
                        file_alias_url)
                    continue

                if principal is None and not handler.allow_unknown_users:
                    _handle_error(
                        'Unknown user: %s ' % mail['From'],
                        file_alias_url, notify=False
                        )
                    continue

                handled = handler.process(mail, email_addr, file_alias)

                if not handled:
                    _handle_error(
                        "Handler found, but message was not handled: %s" % (
                            mail['From'], ),
                        file_alias_url)
                    continue

                # Commit the transaction before deleting the mail in
                # case there are any errors. If an error occur while
                # commiting the transaction, the mail will be deleted in
                # the exception handler.
                trans.commit()
                mailbox.delete(mail_id)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                # This bare except is needed in order to prevent a bug
                # in the email handling from causing the email interface
                # to lock up. If an email causes an unexpected
                # exception, we simply log the error and delete the
                # email, so that it doesn't stop the rest of the emails
                # from being processed.
                _handle_error(
                    "Unhandled exception", file_alias_url)
                log = getLogger('canonical.launchpad.mail')
                if file_alias_url is not None:
                    email_info = file_alias_url
                else:
                    email_info = raw_mail

                log.error(
                    "An exception was raised inside the handler:\n%s" % (
                        email_info),
                    exc_info=True)
    finally:
        log.info("Closing the mail box.")
        mailbox.close()

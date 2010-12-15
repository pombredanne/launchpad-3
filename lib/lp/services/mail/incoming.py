# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Functions dealing with mails coming into Launchpad."""

# pylint: disable-msg=W0631

__metaclass__ = type

from cStringIO import StringIO as cStringIO
import email.errors
from email.utils import (
    getaddresses,
    parseaddr,
    )
import logging
import re
import sys
from uuid import uuid1

import dkim
import dns.exception
import transaction
from zope.component import getUtility
from zope.interface import (
    directlyProvidedBy,
    directlyProvides,
    )

from canonical.launchpad.interfaces.account import AccountStatus
from canonical.launchpad.interfaces.gpghandler import (
    GPGVerificationError,
    IGPGHandler,
    )
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.interfaces.mail import IWeaklyAuthenticatedPrincipal
from canonical.launchpad.interfaces.mailbox import IMailBox
from canonical.launchpad.mail.commands import get_error_message
from canonical.launchpad.mail.helpers import ensure_sane_signature_timestamp
from canonical.launchpad.mailnotification import (
    send_process_error_notification,
    )
from canonical.launchpad.webapp.errorlog import (
    ErrorReportingUtility,
    ScriptRequest,
    )
from canonical.launchpad.webapp.interaction import (
    get_current_principal,
    setupInteraction,
    )
from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
from canonical.librarian.interfaces import UploadFailed
from lp.registry.interfaces.person import IPerson
from lp.services.mail.handlers import mail_handlers
from lp.services.mail.sendmail import do_paranoid_envelope_to_validation
from lp.services.mail.signedmessage import signed_message_from_string

# Match '\n' and '\r' line endings. That is, all '\r' that are not
# followed by a '\n', and all '\n' that are not preceded by a '\r'.
non_canonicalised_line_endings = re.compile('((?<!\r)\n)|(\r(?!\n))')

# Match trailing whitespace.
trailing_whitespace = re.compile(r'[ \t]*((?=\r\n)|$)')


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
    if trailing_whitespace.search(text):
        text = trailing_whitespace.sub('', text)
    return text


class InvalidSignature(Exception):
    """The signature failed to validate."""


class InactiveAccount(Exception):
    """The account for the person sending this email is inactive."""


def extract_address_domain(address):
    realname, email_address = email.utils.parseaddr(address)
    return email_address.split('@')[1]


_trusted_dkim_domains = [
    'gmail.com', 'google.com', 'mail.google.com', 'canonical.com']


def _isDkimDomainTrusted(domain):
    # Really this should come from a dynamically-modifiable
    # configuration, but we don't have such a thing yet.
    #
    # Being listed here means that we trust the domain not to be an open relay
    # or to allow arbitrary intra-domain spoofing.
    return domain in _trusted_dkim_domains


def _authenticateDkim(signed_message):
    """"Attempt DKIM authentication of email; return True if known authentic

    :param signed_message: ISignedMessage
    """

    log = logging.getLogger('mail-authenticate-dkim')
    log.setLevel(logging.DEBUG)
    # uncomment this for easier test debugging
    # log.addHandler(logging.FileHandler('/tmp/dkim.log'))

    dkim_log = cStringIO()
    log.info('Attempting DKIM authentication of message %s from %s'
        % (signed_message['Message-ID'], signed_message['From']))
    signing_details = []
    try:
        # NB: if this fails with a keyword argument error, you need the
        # python-dkim 0.3-3.2 that adds it
        dkim_result = dkim.verify(
            signed_message.parsed_string, dkim_log, details=signing_details)
    except dkim.DKIMException, e:
        log.warning('DKIM error: %r' % (e,))
        dkim_result = False
    except dns.exception.DNSException, e:
        # many of them have lame messages, thus %r
        log.warning('DNS exception: %r' % (e,))
        dkim_result = False
    else:
        log.info('DKIM verification result=%s' % (dkim_result,))
    log.debug('DKIM debug log: %s' % (dkim_log.getvalue(),))
    if not dkim_result:
        return False
    # in addition to the dkim signature being valid, we have to check that it
    # was actually signed by the user's domain.
    if len(signing_details) != 1:
        log.errors(
            'expected exactly one DKIM details record: %r'
            % (signing_details,))
        return False
    signing_domain = signing_details[0]['d']
    from_domain = extract_address_domain(signed_message['From'])
    if signing_domain != from_domain:
        log.warning("DKIM signing domain %s doesn't match From address %s; "
            "disregarding signature"
            % (signing_domain, from_domain))
        return False
    if not _isDkimDomainTrusted(signing_domain):
        log.warning("valid DKIM signature from untrusted domain %s"
            % (signing_domain,))
        return False
    return True


def authenticateEmail(mail,
    signature_timestamp_checker=None):
    """Authenticates an email by verifying the PGP signature.

    The mail is expected to be an ISignedMessage.

    If this completes, it will set the current security principal to be the
    message sender.

    :param signature_timestamp_checker: This callable is
        passed the message signature timestamp, and it can raise an exception if
        it dislikes it (for example as a replay attack.)  This parameter is
        intended for use in tests.  If None, ensure_sane_signature_timestamp
        is used.
    """

    signature = mail.signature

    name, email_addr = parseaddr(mail['From'])
    authutil = getUtility(IPlacelessAuthUtility)
    principal = authutil.getPrincipalByLogin(email_addr)

    # Check that sender is registered in Launchpad and the email is signed.
    if principal is None:
        setupInteraction(authutil.unauthenticatedPrincipal())
        return

    person = IPerson(principal)

    if person.account_status != AccountStatus.ACTIVE:
        raise InactiveAccount(
            "Mail from a user with an inactive account.")

    dkim_result = _authenticateDkim(mail)

    if dkim_result:
        if mail.signature is not None:
            log = logging.getLogger('process-mail')
            log.info('message has gpg signature, therefore not treating DKIM '
                'success as conclusive')
        else:
            setupInteraction(principal, email_addr)
            return principal

    if signature is None:
        # Mark the principal so that application code can check that the
        # user was weakly authenticated.
        directlyProvides(
            principal, directlyProvidedBy(principal),
            IWeaklyAuthenticatedPrincipal)
        setupInteraction(principal, email_addr)
        return principal

    gpghandler = getUtility(IGPGHandler)
    try:
        sig = gpghandler.getVerifiedSignature(
            canonicalise_line_endings(mail.signedContent), signature)
    except GPGVerificationError, e:
        # verifySignature failed to verify the signature.
        raise InvalidSignature("Signature couldn't be verified: %s" % str(e))

    if signature_timestamp_checker is None:
        signature_timestamp_checker = ensure_sane_signature_timestamp
    # If this fails, we return an error to the user rather than just treating
    # it as untrusted, so they can debug or understand the problem.
    signature_timestamp_checker(
        sig.timestamp,
        'incoming mail verification')

    for gpgkey in person.gpg_keys:
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


def handleMail(trans=transaction,
    signature_timestamp_checker=None):
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

    def _handle_user_error(error, mail):
        mailbox.delete(mail_id)
        send_process_error_notification(
            mail['From'], 'Submit Request Failure', str(error), mail)
        trans.commit()

    log = logging.getLogger('process-mail')
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
                file_name = str(uuid1()) + '.txt'
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
                    log = logging.getLogger('lp.services.mail')
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
                        file_alias_url, notify=False)
                    continue
                if mail.get_content_type() == 'multipart/report':
                    # Mails with a content type of multipart/report are
                    # generally DSN messages and should be ignored.
                    _handle_error(
                        "Got a multipart/report message.",
                        file_alias_url, notify=False)
                    continue
                if 'precedence' in mail:
                    _handle_error(
                        "Got a message with a precedence header.",
                        file_alias_url, notify=False)
                    continue

                try:
                    principal = authenticateEmail(
                        mail, signature_timestamp_checker)
                except InvalidSignature, error:
                    _handle_user_error(error, mail)
                    continue
                except InactiveAccount:
                    _handle_error(
                        "Inactive account found for %s" % mail['From'],
                        file_alias_url, notify=False)
                    continue

                # Extract the domain the mail was sent to.  Mails sent to
                # Launchpad should have an X-Launchpad-Original-To header.
                if 'X-Launchpad-Original-To' in mail:
                    addresses = [mail['X-Launchpad-Original-To']]
                else:
                    log = logging.getLogger('lp.services.mail')
                    log.warn(
                        "No X-Launchpad-Original-To header was present "
                        "in email: %s" %
                         file_alias_url)
                    # Process all addresses found as a fall back.
                    cc = mail.get_all('cc') or []
                    to = mail.get_all('to') or []
                    names_addresses = getaddresses(to + cc)
                    addresses = [addr for name, addr in names_addresses]

                try:
                    do_paranoid_envelope_to_validation(addresses)
                except AssertionError, e:
                    _handle_error(
                        "Invalid email address: %s" % e,
                        file_alias_url, notify=False)
                    continue

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
                        file_alias_url, notify=False)
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
                # This bare except is needed in order to prevent any bug
                # in the email handling from causing the email interface
                # to lock up. If an email causes an unexpected
                # exception, we simply log the error and delete the
                # email, so that it doesn't stop the rest of the emails
                # from being processed.
                _handle_error(
                    "Unhandled exception", file_alias_url)
                log = logging.getLogger('canonical.launchpad.mail')
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

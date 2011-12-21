# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# XXX: Gavin Panella 2008-11-21 bug=300725: This module need
# refactoring and/or splitting into a package or packages.

"""Event handlers that send email notifications."""

__metaclass__ = type

from difflib import unified_diff
from email import message_from_string
from email.MIMEMessage import MIMEMessage
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
import re

from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import block_implicit_flushes
from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.webapp.interfaces import ILaunchpadRoot
from canonical.launchpad.webapp.publisher import canonical_url
from lp.bugs.mail.bugnotificationbuilder import get_bugmail_error_address
from lp.services.mail.mailwrapper import MailWrapper
# XXX 2010-06-16 gmb bug=594985
#     This shouldn't be here, but if we take it out lots of things cry,
#     which is sad.
from lp.services.mail.notificationrecipientset import NotificationRecipientSet
from lp.services.mail.sendmail import (
    format_address,
    sendmail,
    simple_sendmail,
    )

# Silence lint warnings.
NotificationRecipientSet


CC = "CC"
MAX_RETURN_MESSAGE_SIZE = config.processmail.max_error_message_return_size


def send_process_error_notification(to_address, subject, error_msg,
                                    original_msg, failing_command=None,
                                    max_return_size=MAX_RETURN_MESSAGE_SIZE):
    """Send a mail about an error occurring while using the email interface.

    Tells the user that an error was encountered while processing his
    request and attaches the original email which caused the error to
    happen.  The original message will be truncated to
    max_return_size bytes.

        :to_address: The address to send the notification to.
        :subject: The subject of the notification.
        :error_msg: The error message that explains the error.
        :original_msg: The original message sent by the user.
        :failing_command: The command that caused the error to happen.
        :max_return_size: The maximum size returned for the original message.
    """
    if isinstance(failing_command, list):
        failing_commands = failing_command
    elif failing_command is None:
        failing_commands = []
    else:
        failing_commands = [failing_command]
    failed_commands_information = ''
    if len(failing_commands) > 0:
        failed_commands_information = 'Failing command:'
        for failing_command in failing_commands:
            failed_commands_information += '\n    %s' % str(failing_command)

    body = get_email_template(
        'email-processing-error.txt', app='services/mail') % {
            'failed_command_information': failed_commands_information,
            'error_msg': error_msg}
    mailwrapper = MailWrapper(width=72)
    body = mailwrapper.format(body)
    error_part = MIMEText(body.encode('utf-8'), 'plain', 'utf-8')

    msg = MIMEMultipart()
    msg['To'] = to_address
    msg['From'] = get_bugmail_error_address()
    msg['Subject'] = subject
    msg.attach(error_part)
    original_msg_str = str(original_msg)
    if len(original_msg_str) > max_return_size:
        truncated_msg_str = original_msg_str[:max_return_size]
        original_msg = message_from_string(truncated_msg_str)
    msg.attach(MIMEMessage(original_msg))
    sendmail(msg)


def get_unified_diff(old_text, new_text, text_width):
    r"""Return a unified diff of the two texts.

    Before the diff is produced, the texts are wrapped to the given text
    width.

        >>> print get_unified_diff(
        ...     'Some text\nAnother line\n',get_un
        ...     'Some more text\nAnother line\n',
        ...     text_width=72)
        - Some text
        + Some more text
          Another line

    """
    mailwrapper = MailWrapper(width=72)
    old_text_wrapped = mailwrapper.format(old_text or '')
    new_text_wrapped = mailwrapper.format(new_text or '')

    lines_of_context = len(old_text_wrapped.splitlines())
    text_diff = unified_diff(
        old_text_wrapped.splitlines(),
        new_text_wrapped.splitlines(),
        n=lines_of_context)
    # Remove the diff header, which consists of the first three
    # lines.
    text_diff = list(text_diff)[3:]
    # Let's simplify the diff output by removing the helper lines,
    # which begin with '?'.
    text_diff = [
        diff_line for diff_line in text_diff
        if not diff_line.startswith('?')]
    # Add a whitespace between the +/- and the text line.
    text_diff = [
        re.sub('^([\+\- ])(.*)', r'\1 \2', line)
        for line in text_diff]
    text_diff = '\n'.join(text_diff)
    return text_diff


@block_implicit_flushes
def notify_new_ppa_subscription(subscription, event):
    """Notification that a new PPA subscription can be activated."""
    non_active_subscribers = subscription.getNonActiveSubscribers()

    archive = subscription.archive

    # We don't send notification emails for commercial PPAs as these
    # are purchased via software center (and do not mention Launchpad).
    if archive.commercial:
        return

    registrant_name = subscription.registrant.displayname
    ppa_displayname = archive.displayname
    ppa_reference = "ppa:%s/%s" % (
        archive.owner.name, archive.name)
    ppa_description = archive.description
    subject = 'PPA access granted for ' + ppa_displayname

    template = get_email_template('ppa-subscription-new.txt', app='soyuz')

    for person, preferred_email in non_active_subscribers:
        to_address = [preferred_email.email]
        root = getUtility(ILaunchpadRoot)
        recipient_subscriptions_url = "%s~/+archivesubscriptions" % (
            canonical_url(root))
        description_blurb = '.'
        if ppa_description is not None and ppa_description != '':
            description_blurb = (
                ' and has the following description:\n\n%s' % ppa_description)
        replacements = {
            'recipient_name': person.displayname,
            'registrant_name': registrant_name,
            'registrant_profile_url': canonical_url(subscription.registrant),
            'ppa_displayname': ppa_displayname,
            'ppa_reference': ppa_reference,
            'ppa_description_blurb': description_blurb,
            'recipient_subscriptions_url': recipient_subscriptions_url,
            }
        body = MailWrapper(72).format(template % replacements,
                                      force_wrap=True)

        from_address = format_address(
            registrant_name, config.canonical.noreply_from_address)

        headers = {
            'Sender': config.canonical.bounce_address,
            }

        # If the registrant has a preferred email, then use it for the
        # Reply-To.
        if subscription.registrant.preferredemail:
            headers['Reply-To'] = format_address(
                registrant_name,
                subscription.registrant.preferredemail.email)

        simple_sendmail(from_address, to_address, subject, body, headers)
